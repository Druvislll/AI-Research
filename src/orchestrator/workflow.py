"""工作流编排器 - 协调采集→知识库→报告的全流程"""

import asyncio
from datetime import datetime
from typing import Optional
from src.collector.web_scraper import WebScraper
from src.collector.search_collector import SearchCollector
from src.collector.doc_parser import DocParser
from src.collector.link_importer import LinkImporter
from src.knowledge_base.models import KnowledgeBase
from src.knowledge_base.vector_store import VectorStore
from src.knowledge_base.retriever import Retriever
from src.knowledge_base.text_splitter import ParentChildSplitter
from src.report.generator import ReportGenerator
from src import config


class ResearchWorkflow:
    """行业研究完整工作流"""

    def __init__(self, parent_size: int = 1000, parent_overlap: int = 200,
                 child_size: int = 250, child_overlap: int = 50):
        self.web_scraper = WebScraper()
        self.search_collector = SearchCollector()
        self.doc_parser = DocParser()
        self.link_importer = LinkImporter()
        self.kb = KnowledgeBase()
        self.vector_store = VectorStore()
        self.retriever = Retriever()
        self.report_generator = ReportGenerator()
        self.splitter = ParentChildSplitter(
            parent_size=parent_size, parent_overlap=parent_overlap,
            child_size=child_size, child_overlap=child_overlap,
        )

    def create_industry(self, name: str, focus: str = "", report_type: str = "周报") -> int:
        """创建或获取行业"""
        return self.kb.create_industry(name, focus, report_type)

    async def run_collection(self, industry_id: int, queries: list[str] = None) -> dict:
        """执行信息采集"""
        industry = self.kb.get_industry(industry_id)
        if not industry:
            return {"success": False, "message": "行业不存在"}

        name = industry["name"]
        if not queries:
            queries = [name, f"{name} 最新动态", f"{name} 行业新闻"]

        results = {"web": [], "search": [], "total": 0}

        # 1. 搜索引擎搜索
        search_results = await self.search_collector.batch_search(queries)
        results["search"] = search_results
        for item in search_results:
            self.kb.add_source(industry_id, item)

        # 2. 抓取搜索结果中的网页内容（取前 10 个有效 URL）
        urls_to_scrape = []
        for item in search_results:
            if item.get("url") and not item.get("content"):
                urls_to_scrape.append(item["url"])
            if len(urls_to_scrape) >= 10:
                break

        if urls_to_scrape:
            scraped = await self.web_scraper.scrape_urls(urls_to_scrape)
            results["web"] = scraped
            for item in scraped:
                if item.get("content"):
                    self.kb.add_source(industry_id, item)

        results["total"] = len(results["search"]) + len(results["web"])
        return {"success": True, "data": results}

    def build_knowledge_base(self, industry_id: int) -> dict:
        """基于采集的原始资料构建知识库（父子分块，自动跳过已处理的来源）

        父块 → SQLite（完整上下文，供报告生成使用）
        子块 → ChromaDB（精确检索，命中子块后返回所属父块）
        """
        sources = self.kb.get_sources(industry_id)
        if not sources:
            return {"success": False, "message": "没有采集到的资料", "count": 0}

        # 获取已处理的 source_id，跳过重复
        existing_entries = self.kb.get_knowledge_entries(industry_id)
        processed_source_ids = {e["source_id"] for e in existing_entries}
        skipped = 0

        added_parents = 0
        added_children = 0
        child_ids = []
        child_texts = []
        child_metadatas = []

        for source in sources:
            source_id = source.get("source_id", "")

            # 跳过已处理的来源
            if source_id in processed_source_ids:
                skipped += 1
                continue

            title = source.get("title", "未知")
            content = source.get("content", "")
            url = source.get("url", "")

            if not content or len(content) < 20:
                continue

            # 父子分块
            pairs = self.splitter.split_text(content)

            for pi, pair in enumerate(pairs):
                parent_text = pair["parent"]
                children = pair["children"]
                parent_id = f"{source_id}_p{pi}"

                # 父块 → SQLite（完整的上下文）
                parent_entry = {
                    "source_id": source_id,
                    "title": title,
                    "summary": parent_text[:200],
                    "tags": source.get("tags", ""),
                    "content": parent_text,
                    "url": url,
                    "vector_id": parent_id,
                }
                self.kb.add_knowledge_entry(industry_id, parent_entry)
                added_parents += 1

                # 子块 → ChromaDB（精确检索，带 parent_text 元数据）
                for ci, child_text in enumerate(children):
                    child_id = f"{parent_id}_c{ci}"
                    child_ids.append(child_id)
                    child_texts.append(f"{title}\n{child_text}")
                    child_metadatas.append({
                        "child_id": child_id,
                        "parent_id": parent_id,
                        "parent_text": parent_text,  # 关键：子块携带父块完整文本
                        "title": title,
                        "source_id": source_id,
                        "url": url,
                        "industry_id": str(industry_id),
                    })
                    added_children += 1

        # 批量存入向量库（只存子块）
        if child_ids:
            self.vector_store.add_documents(child_ids, child_texts, child_metadatas)

        skip_info = f"，跳过 {skipped} 个重复来源" if skipped else ""
        return {
            "success": True,
            "count": added_parents + added_children,
            "parents": added_parents,
            "children": added_children,
            "message": f"已构建 {added_parents} 个父块 × {added_children} 个子块{skip_info}",
        }

    def generate_report(self, industry_id: int) -> dict:
        """生成行业研究报告"""
        content = self.report_generator.generate(industry_id)
        report_id = self.report_generator.save_report(industry_id, content)
        return {
            "success": True,
            "report_id": report_id,
            "content": content,
            "message": "报告生成成功",
        }

    async def run_full_workflow(
        self,
        industry_name: str,
        focus: str = "",
        queries: list[str] = None,
    ) -> dict:
        """一键执行完整工作流"""
        steps = []

        # Step 1: 创建行业
        industry_id = self.create_industry(industry_name, focus)
        steps.append({"step": "1/4", "name": "创建行业", "status": "done", "detail": industry_name})

        # Step 2: 采集信息
        collect_result = await self.run_collection(industry_id, queries)
        steps.append({
            "step": "2/4",
            "name": "信息采集",
            "status": "done",
            "detail": f"采集到 {collect_result['data']['total'] if collect_result['success'] else 0} 条信息",
        })

        # Step 3: 构建知识库
        kb_result = self.build_knowledge_base(industry_id)
        steps.append({
            "step": "3/4",
            "name": "知识库构建",
            "status": "done",
            "detail": kb_result.get("message", ""),
        })

        # Step 4: 生成报告
        report_result = self.generate_report(industry_id)
        steps.append({
            "step": "4/4",
            "name": "报告生成",
            "status": "done",
            "detail": "报告已生成",
        })

        return {
            "success": True,
            "industry_id": industry_id,
            "steps": steps,
            "report_content": report_result["content"],
            "report_id": report_result["report_id"],
        }
