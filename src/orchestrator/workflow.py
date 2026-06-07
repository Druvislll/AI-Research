"""工作流编排器 - 协调采集→知识库→报告的全流程"""

import asyncio
from datetime import datetime
from src.collector.web_scraper import WebScraper
from src.collector.search_collector import SearchCollector
from src.collector.doc_parser import DocParser
from src.collector.link_importer import LinkImporter
from src.knowledge_base.models import KnowledgeBase
from src.knowledge_base.vector_store import VectorStore
from src.knowledge_base.retriever import Retriever
from src.knowledge_base.text_splitter import ParentChildSplitter
from src.knowledge_base.source_filter import filter_source
from src.report.generator import ReportGenerator
from src.utils.logger import log
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
        return self.kb.create_industry(name, focus, report_type)

    def _build_queries(self, name: str, focus: str = "") -> list[str]:
        """根据行业名和关注方向生成搜索词"""
        queries = [name]
        if focus:
            for f in focus.split(", "):
                f = f.strip()
                if f:
                    queries.append(f"{name} {f}")
        queries.append(f"{name} 最新动态")
        queries.append(f"{name} 行业新闻")
        return queries

    async def run_collection(self, industry_id: int, queries: list[str] = None) -> dict:
        """执行信息采集（含信源评分过滤）"""
        industry = self.kb.get_industry(industry_id)
        if not industry:
            return {"success": False, "message": "行业不存在"}

        name = industry["name"]
        if not queries:
            queries = self._build_queries(name, industry.get("focus", ""))

        log.info(f"采集开始 | 行业: {name} | 查询词: {len(queries)}个")
        results = {"web": [], "search": [], "filtered": 0, "total": 0}

        # 1. 搜索引擎搜索
        try:
            search_results = await self.search_collector.batch_search(queries)
            log.info(f"  搜索完成 | 原始结果: {len(search_results)}条")
        except Exception as e:
            log.error(f"  搜索失败: {e}")
            search_results = []

        for item in search_results:
            item = filter_source(item, min_score=3)
            if item:
                self.kb.add_source(industry_id, item)
                results["search"].append(item)
            else:
                results["filtered"] += 1

        # 2. 抓取搜索结果中的网页内容
        urls_to_scrape = []
        for item in search_results:
            if item and item.get("url"):
                urls_to_scrape.append(item["url"])
            if len(urls_to_scrape) >= 10:
                break

        if urls_to_scrape:
            try:
                scraped = await self.web_scraper.scrape_urls(urls_to_scrape)
                log.info(f"  抓取完成 | 目标: {len(urls_to_scrape)}个 | 成功: {len(scraped)}个")
            except Exception as e:
                log.error(f"  抓取失败: {e}")
                scraped = []

            for item in scraped:
                if not item.get("content"):
                    continue
                item = filter_source(item, min_score=3)
                if item:
                    self.kb.add_source(industry_id, item)
                    results["web"].append(item)
                else:
                    results["filtered"] += 1

        results["total"] = len(results["search"]) + len(results["web"])
        log.info(f"采集完成 | 入库: {results['total']}条 | 过滤: {results['filtered']}条")
        return {"success": True, "data": results}

    def build_knowledge_base(self, industry_id: int) -> dict:
        """构建知识库（父子分块，自动跳过已处理的来源，含异常回退）"""
        try:
            sources = self.kb.get_sources(industry_id)
            if not sources:
                return {"success": False, "message": "没有采集到的资料", "count": 0}

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
                if source_id in processed_source_ids:
                    skipped += 1
                    continue

                title = source.get("title", "未知")
                content = source.get("content", "")
                url = source.get("url", "")

                if not content or len(content) < 20:
                    continue

                try:
                    pairs = self.splitter.split_text(content)
                except Exception as e:
                    log.warning(f"  分块失败 ({source_id[:12]}): {e}")
                    continue

                for pi, pair in enumerate(pairs):
                    parent_text = pair["parent"]
                    children = pair["children"]
                    parent_id = f"{source_id}_p{pi}"

                    parent_entry = {
                        "source_id": source_id, "title": title,
                        "summary": parent_text[:200], "tags": source.get("tags", ""),
                        "content": parent_text, "url": url, "vector_id": parent_id,
                    }
                    try:
                        self.kb.add_knowledge_entry(industry_id, parent_entry)
                        added_parents += 1
                    except Exception as e:
                        log.warning(f"  父块入库失败: {e}")
                        continue

                    for ci, child_text in enumerate(children):
                        child_id = f"{parent_id}_c{ci}"
                        child_ids.append(child_id)
                        child_texts.append(f"{title}\n{child_text}")
                        child_metadatas.append({
                            "child_id": child_id, "parent_id": parent_id,
                            "parent_text": parent_text, "title": title,
                            "source_id": source_id, "url": url,
                            "industry_id": str(industry_id),
                        })
                        added_children += 1

            # ChromaDB 写入（失败不回滚 SQLite）
            if child_ids:
                try:
                    self.vector_store.add_documents(child_ids, child_texts, child_metadatas)
                except Exception as e:
                    log.warning(f"  ChromaDB 写入失败，SQLite 数据已保留: {e}")

            skip_info = f"，跳过 {skipped} 个重复" if skipped else ""
            log.info(f"知识库构建完成 | 父块: {added_parents} | 子块: {added_children}{skip_info}")
            return {
                "success": True, "count": added_parents + added_children,
                "parents": added_parents, "children": added_children,
                "message": f"已构建 {added_parents} 个父块 × {added_children} 个子块{skip_info}",
            }
        except Exception as e:
            log.error(f"知识库构建失败: {e}")
            return {"success": False, "message": f"知识库构建出错: {e}", "count": 0}

    def generate_report(self, industry_id: int) -> dict:
        """生成报告（含重试）"""
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                content = self.report_generator.generate(industry_id)
                report_id = self.report_generator.save_report(industry_id, content)
                log.info(f"报告生成成功 | id={report_id}")
                return {
                    "success": True, "report_id": report_id,
                    "content": content, "message": "报告生成成功",
                }
            except Exception as e:
                log.warning(f"  报告生成失败{'，正在重试...' if attempt < max_retries else ''}: {e}")
                if attempt >= max_retries:
                    return {"success": False, "message": f"报告生成出错: {e}", "content": ""}

    async def run_full_workflow(self, industry_name: str, focus: str = "",
                                 queries: list[str] = None) -> dict:
        """一键执行完整工作流"""
        log.info(f"====== 开始完整工作流 | 行业: {industry_name} ======")
        steps = []

        try:
            industry_id = self.create_industry(industry_name, focus)
            steps.append({"step": "1/4", "name": "创建行业", "status": "done", "detail": industry_name})

            collect_result = await self.run_collection(industry_id, queries)
            steps.append({
                "step": "2/4", "name": "信息采集", "status": "done",
                "detail": f"采集到 {collect_result['data']['total'] if collect_result['success'] else 0} 条信息",
            })

            kb_result = self.build_knowledge_base(industry_id)
            steps.append({
                "step": "3/4", "name": "知识库构建", "status": "done",
                "detail": kb_result.get("message", ""),
            })

            report_result = self.generate_report(industry_id)
            steps.append({
                "step": "4/4", "name": "报告生成", "status": "done",
                "detail": report_result.get("message", "报告生成成功"),
            })

            log.info(f"====== 工作流完成 ======")
            return {
                "success": report_result.get("success", False),
                "industry_id": industry_id, "steps": steps,
                "report_content": report_result.get("content", ""),
                "report_id": report_result.get("report_id", 0),
            }
        except Exception as e:
            log.error(f"工作流异常: {e}")
            return {"success": False, "steps": steps, "report_content": "", "report_id": 0}
