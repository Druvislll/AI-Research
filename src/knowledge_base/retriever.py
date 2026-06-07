"""知识库检索器 - 父子分块检索"""

from src.knowledge_base.models import KnowledgeBase
from src.knowledge_base.vector_store import VectorStore


class Retriever:
    """知识检索器，使用父子分块策略：

    搜索 → 命中子块（精确） → 聚合成父块（完整上下文） → 返回
    """

    def __init__(self):
        self.vector_store = VectorStore()
        self.kb = KnowledgeBase()

    def search(self, query: str, industry_id: int, top_k: int = 10) -> list[dict]:
        """基于子块语义搜索，返回去重后的父块结果"""
        return self.vector_store.search_parents(query, top_k=top_k)

    def get_context_for_report(self, industry_id: int, top_k: int = 20) -> tuple[str, list[dict]]:
        """获取用于报告生成的上下文（父子分块检索）"""
        industry = self.kb.get_industry(industry_id)
        if not industry:
            return "暂无相关行业数据。", []

        # 如果没有子块（旧数据），回退到 knowledge_entries
        entries = self.kb.get_knowledge_entries(industry_id)
        if not entries:
            entries = self.kb.get_sources(industry_id)

        if not entries:
            return "暂未收集到该行业的相关信息。", []

        # 构建上下文文本（如果已有父块，优先用父块；否则回退到旧条目）
        context_parts = []
        seen_texts = set()
        for e in entries[:top_k]:
            title = e.get("title", "未知标题")
            content = e.get("content", e.get("summary", ""))[:500]
            url = e.get("url", "")
            # 去重
            key = content[:100]
            if key in seen_texts:
                continue
            seen_texts.add(key)
            context_parts.append(f"### {title}\n{content}\n来源: {url}")

        context = f"行业: {industry['name']}\n关注方向: {industry.get('focus', '全部')}\n\n" + \
                  "\n\n---\n\n".join(context_parts)

        return context, entries
