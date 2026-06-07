"""报告生成器 - 基于知识库调用 LLM 生成结构化报告"""

from datetime import datetime
from src.llm import LLMClient
from src.knowledge_base.retriever import Retriever
from src.knowledge_base.models import KnowledgeBase
from src.report.templates import get_empty_section
from src.utils.logger import log
from src import config


class ReportGenerator:
    """行业研究报告生成器"""

    def __init__(self):
        self.llm = LLMClient()
        self.retriever = Retriever()
        self.kb = KnowledgeBase()

    def generate(self, industry_id: int) -> str:
        """生成完整行业研究报告"""
        industry = self.kb.get_industry(industry_id)
        if not industry:
            return "错误：未找到该行业信息"

        # 获取知识库上下文（带 [N] 引用编号）
        context, indexed_entries = self.retriever.get_context_for_report(industry_id, top_k=30)

        log.info(f"报告生成 | 行业: {industry['name']} | 知识条目: {len(indexed_entries)}条")

        report_content = self._generate_report(
            industry_name=industry["name"],
            focus=industry.get("focus", "全部"),
            context=context,
        )

        # 追加完整来源列表（带 [N] 编号）
        sources_section = self._format_sources(indexed_entries)
        report_content += "\n\n## 八、信息来源\n" + sources_section

        return report_content

    def _generate_report(self, industry_name: str, focus: str, context: str) -> str:
        """调用 LLM 生成报告"""
        system_prompt = """你是一位资深的行业研究分析师，擅长撰写专业、结构化的行业研究报告。

报告要求：
1. 语言专业、客观、数据驱动
2. 每个观点都要有信息来源支撑，在引用时用 [N] 标注来源编号
3. 按照指定的章节结构输出
4. 尽量避免空泛的描述，提供具体的信息和判断
5. 如果某方面信息不足，如实说明

引用规则：
- 每条参考信息前面有 [1] [2] [3] 等编号
- 在报告中引用时，在句末标注对应的编号，例如：
  "2025年中国新能源汽车销量突破2000万辆[1]，同比增长35%[2]。"
- 同一信息在正文中多次引用时，每次都要标注编号
- 确保每个关键数据/事实都有来源引用"""

        user_prompt = f"""行业名称：{industry_name}
关注方向：{focus}
参考信息（每条带 [N] 编号）：

{context}

请按照以下模板生成报告（每个章节请填充实际内容，引用时标注 [N] 编号）：

# {industry_name}行业研究报告（周报）

## 一、行业概览
[简要说明行业背景、范围和当前发展阶段]

## 二、本周核心摘要
[列出本周最重要的3-5条变化，每条一行]

## 三、重要事件
[按类别列出事件：政策/市场/公司/技术/融资/风险]

## 四、趋势判断
[基于以上信息，总结行业近期变化趋势]

## 五、重点公司动态
[汇总行业内重点企业动态]

## 六、机会与风险
[分析市场机会和潜在风险]

## 七、战略建议
[面向企业客户的可参考行动建议]"""

        log.info(f"  LLM 调用 | 模型: {self.llm.model} | 上下文: {len(context)}字")
        result = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=8192,
        )
        log.info(f"  LLM 返回 | 报告长度: {len(result)}字")
        return result

    def _format_sources(self, entries: list[dict]) -> str:
        """格式化信息来源（带 [N] 编号）"""
        sources = []
        seen = set()
        for e in entries:
            ref_idx = e.get("_ref_index", 0)
            url = e.get("url", "")
            title = e.get("title", "未知来源")

            if not url or url in seen:
                continue
            seen.add(url)

            from urllib.parse import urlparse
            try:
                domain = urlparse(url).netloc
            except Exception:
                domain = ""

            sources.append(f"[{ref_idx}] {title}  ({domain})\n    {url}")

        if not sources:
            return get_empty_section("信息来源")

        return "\n\n".join(sources)

    def save_report(self, industry_id: int, content: str) -> int:
        """保存报告到数据库和文件"""
        industry = self.kb.get_industry(industry_id)
        title = f"{industry['name']}行业研究报告 - {datetime.now().strftime('%Y-%m-%d')}"

        report_id = self.kb.add_report(industry_id, title, content)

        from pathlib import Path
        report_dir = config.REPORTS_DIR / industry["name"]
        report_dir.mkdir(parents=True, exist_ok=True)
        file_path = report_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file_path.write_text(content, encoding="utf-8")

        log.info(f"  报告已保存 | id={report_id} | {file_path.name}")
        return report_id
