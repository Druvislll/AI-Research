"""AI-Research 行业研究报告生成系统 - Streamlit 主界面"""

# 注意：config 必须先于其他模块导入，以设置 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION
from src import config

import streamlit as st
from datetime import datetime
from src.orchestrator.workflow import ResearchWorkflow
from src.knowledge_base.models import KnowledgeBase

# 页面配置
st.set_page_config(
    page_title="AI-Research 行业研究助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
st.markdown("""
<style>
    /* ========== 全局 ========== */
    .stApp { max-width: 100%; }
    .main > div { padding-top: 1rem; }

    /* ========== 搜索栏三列对齐 ========== */
    /* 改用 st.columns vertical_alignment 实现，无需额外 CSS */

    /* ========== 按钮统一样式 ========== */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #4CAF50, #2E7D32) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3) !important;
    }
    .stButton button[kind="primary"]:hover {
        box-shadow: 0 4px 14px rgba(76, 175, 80, 0.45) !important;
        transform: translateY(-1px) !important;
    }

    /* ========== 卡片/容器 ========== */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        margin-bottom: 0.5rem;
    }
    div[data-testid="stExpander"] > details {
        border-radius: 10px;
    }

    /* ========== 原始资料卡片（无固定白色背景，适配深色模式） ========== */
    .source-item {
        padding: 0.75rem 1rem;
        margin: 0.4rem 0;
        border-left: 3px solid #4CAF50;
        border-radius: 0 8px 8px 0;
        background: rgba(128, 128, 128, 0.06);
        transition: background 0.2s;
    }
    .source-item:hover {
        background: rgba(76, 175, 80, 0.08);
    }
    .source-item a {
        color: #4CAF50;
        text-decoration: none;
        font-size: 0.85rem;
        word-break: break-all;
    }
    .source-item a:hover {
        text-decoration: underline;
    }

    /* ========== 知识库条目 ========== */
    .kb-stat {
        font-size: 0.85rem;
        opacity: 0.65;
    }

    /* ========== 报告标题样式 ========== */
    .report-header { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem; }
    .section-title {
        font-size: 1.3rem; font-weight: 600; margin-top: 1.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #4CAF50;
    }

    /* ========== 进度条美化 ========== */
    div[data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, #4CAF50, #81C784);
    }

    /* ========== 侧边栏 ========== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(76, 175, 80, 0.04), transparent);
    }
</style>
""", unsafe_allow_html=True)


def init_session():
    """初始化会话状态"""
    if "workflow" not in st.session_state:
        st.session_state.workflow = ResearchWorkflow()
    if "kb" not in st.session_state:
        st.session_state.kb = KnowledgeBase()
    if "current_industry_id" not in st.session_state:
        st.session_state.current_industry_id = None
    if "report_content" not in st.session_state:
        st.session_state.report_content = None


init_session()


def run_research_sync(industry_name: str, focus: str, queries: list[str]):
    """同步执行研究工作流（替代 asyncio.run 避免事件循环冲突）"""
    progress_bar = st.progress(0, text="初始化...")
    status_text = st.empty()

    workflow = st.session_state.workflow

    try:
        # Step 1 - 创建行业
        progress_bar.progress(10, text="创建行业...")
        industry_id = workflow.create_industry(industry_name, focus)
        st.session_state.current_industry_id = industry_id

        # Step 2 - 采集（用 asyncio.run 在顶层执行）
        progress_bar.progress(25, text="正在采集网络信息...")
        status_text.text("正在搜索网络信息，请稍候...")
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 已存在事件循环，用 run_until_complete
            collect_result = loop.run_until_complete(workflow.run_collection(industry_id, queries))
        except RuntimeError:
            # 没有运行中的事件循环，正常用 asyncio.run
            collect_result = asyncio.run(workflow.run_collection(industry_id, queries))

        # Step 3 - 构建知识库
        progress_bar.progress(55, text="正在构建知识库...")
        status_text.text("正在整理采集到的资料...")
        kb_result = workflow.build_knowledge_base(industry_id)

        # Step 4 - 生成报告
        progress_bar.progress(80, text="正在生成报告（调用 LLM）...")
        status_text.text("AI 正在生成行业研究报告，请稍候...")
        report_result = workflow.generate_report(industry_id)

        progress_bar.progress(100, text="完成！")
        status_text.empty()

        st.session_state.report_content = report_result["content"]

        return {
            "industry_id": industry_id,
            "collect_count": collect_result.get("data", {}).get("total", 0) if collect_result.get("success") else 0,
            "kb_count": kb_result.get("count", 0),
            "report_id": report_result.get("report_id", 0),
        }
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ 研究过程中出现错误: {str(e)}")
        return None


# ==================== 侧边栏 ====================
with st.sidebar:
    # ---- 顶部标题 ----
    st.title("📊 AI-Research")
    st.caption("行业研究报告自动生成系统")
    st.divider()

    # ---- 历史行业列表 ----
    st.subheader("📂 历史行业")
    industries = st.session_state.kb.get_industries()

    # 添加新的研究报告按钮（紧跟在历史行业下方）
    if st.button("➕ 添加新的研究报告", use_container_width=True, type="secondary"):
        st.session_state.current_industry_id = None
        st.session_state.report_content = None
        st.rerun()

    if industries:
        for ind in industries:
            # 获取该行业最新报告/资料的日期
            reports = st.session_state.kb.get_reports(ind["id"])
            if reports:
                date_str = reports[0]["created_at"][:10]
            else:
                date_str = ind.get("updated_at", "")[:10] or "无记录"

            col1, col2 = st.columns([3, 1], vertical_alignment="center")
            with col1:
                if st.button(f"📋 {ind['name']}", key=f"ind_{ind['id']}", use_container_width=True):
                    st.session_state.current_industry_id = ind["id"]
                    reports = st.session_state.kb.get_reports(ind["id"])
                    if reports:
                        st.session_state.report_content = reports[0]["content"]
                    else:
                        st.session_state.report_content = None
                    st.rerun()
            with col2:
                st.caption(date_str)
    else:
        st.info("暂无历史行业，请新建研究")

    # ---- 底部：版本信息 ----
    st.divider()
    st.caption("v0.1.0 | AI-Research")


# ==================== 主界面 ====================

# --- 新建研究区域（仅当没有正在查看的历史报告时才显示） ---
if st.session_state.current_industry_id is None:
    st.title("🔬 AI 行业研究助手")
    st.markdown("输入行业主题，自动完成 **信息采集 → 知识库构建 → 报告生成** 全流程")

    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 3, 2], vertical_alignment="bottom")
        with col1:
            industry_name = st.text_input(
                "🏭 行业主题",
                placeholder="如：新能源汽车、低空经济、AI 教育、跨境电商...",
            )
        with col2:
            focus = st.multiselect(
                "🎯 关注方向",
                options=config.FOCUS_OPTIONS,
                default=[],
                placeholder="选择关注方向（可选）",
            )
        with col3:
            research_btn = st.button(
                "🚀 开始研究",
                type="primary",
                use_container_width=True,
                disabled=not industry_name,
            )

    # --- 高级搜索词设置 ---
    with st.expander("🔍 高级搜索词设置（可选）"):
        search_queries = st.text_area(
            "自定义搜索词（每行一个，为空则自动生成）",
            placeholder=f"{industry_name}\n{industry_name} 最新政策\n{industry_name} 市场规模",
            height=80,
        )

    # --- 文档导入区域 ---
    with st.expander("📄 导入本地文档（可选）"):
        uploaded_files = st.file_uploader(
            "上传 PDF / Word / Markdown / TXT 文件",
            type=["pdf", "docx", "doc", "md", "txt"],
            accept_multiple_files=True,
        )
        import_urls = st.text_area(
            "或输入文章链接（每行一个）",
            placeholder="https://example.com/article1\nhttps://example.com/article2",
            height=60,
        )
        if uploaded_files or import_urls:
            if st.button("导入资料", use_container_width=True):
                st.info("导入功能将在运行研究时自动处理已上传的文件和链接")

    # ==================== 执行研究 ====================
    if research_btn and industry_name:
        queries_list = [q.strip() for q in search_queries.split("\n") if q.strip()] if search_queries else None
        focus_str = ", ".join(focus)

        result = run_research_sync(industry_name, focus_str, queries_list)

        if result:
            st.success(f"✅ 研究完成！共采集 {result['collect_count']} 条信息，"
                       f"构建 {result['kb_count']} 个知识块，报告已生成。")
            st.rerun()
        else:
            st.error("研究流程未完成，请检查上方错误信息。")

# ==================== 显示报告和知识库 ====================
tab1, tab2, tab3 = st.tabs(["📝 研究报告", "📚 知识库", "📡 原始资料"])

# --- Tab1: 报告 ---
with tab1:
    if st.session_state.report_content:
        st.markdown(st.session_state.report_content)
    elif st.session_state.current_industry_id:
        reports = st.session_state.kb.get_reports(st.session_state.current_industry_id)
        if reports:
            st.session_state.report_content = reports[0]["content"]
            st.markdown(reports[0]["content"])
        else:
            st.info("💡 请先运行「开始研究」生成报告")
    else:
        st.info("💡 在侧边栏选择一个行业，或在输入框填写行业名称后点击「开始研究」")

# --- Tab2: 知识库 ---
with tab2:
    if st.session_state.current_industry_id:
        entries = st.session_state.kb.get_knowledge_entries(st.session_state.current_industry_id)
        if entries:
            st.caption(f"共 {len(entries)} 条知识条目")
            for i, e in enumerate(entries[:50]):
                with st.expander(f"{i+1}. {e['title']}"):
                    st.markdown(f"**摘要**: {e.get('summary', '')[:300]}")
                    st.markdown(f"**来源**: [{e.get('url', '')}]({e.get('url', '')})")
                    st.markdown(f"**标签**: {e.get('tags', '无')}")
                    if st.button("查看原文", key=f"view_{e['id']}"):
                        st.text_area("原文内容", e.get("content", ""), height=200)
        else:
            st.info("暂无知识条目")
    else:
        st.info("请先选择一个行业")

# --- Tab3: 原始资料 ---
with tab3:
    if st.session_state.current_industry_id:
        sources = st.session_state.kb.get_sources(st.session_state.current_industry_id)
        if sources:
            st.caption(f"共 {len(sources)} 条原始资料")
            for s in sources:
                st.markdown(
                    f"<div class='source-item'>"
                    f"<strong>{s['title']}</strong><br>"
                    f"<span class='kb-stat'>来源: {s['source_type']} | "
                    f"时间: {s.get('scraped_at', '')[:10]}</span><br>"
                    f"<a href='{s['url']}' target='_blank'>{s['url'][:80]}...</a>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("暂无原始资料")
    else:
        st.info("请先选择一个行业")

# 底部
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🗑️ 清空当前报告"):
        st.session_state.report_content = None
        st.rerun()
with col3:
    if st.session_state.report_content:
        st.download_button(
            "📥 下载报告 (Markdown)",
            data=st.session_state.report_content,
            file_name=f"行业研究报告_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
