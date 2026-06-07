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

# 自定义 CSS（参考 szbring.ai 设计风格）
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* 去掉输入框聚焦时的 outline 和 box-shadow */
    html body #root input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    html body #root .stMultiSelect *:focus,
    html body #root .stMultiSelect *:focus-within {
        outline: none !important;
        box-shadow: none !important;
    }

    :root {
        --primary: #0088cc;
        --primary-light: #00a0e9;
        --primary-dark: #006699;
        --accent: #00c6ff;
        --bg: #ffffff;
        --bg-alt: #f8fafc;
        --text: #1e293b;
        --text2: #475569;
        --text3: #94a3b8;
        --border: rgba(0,0,0,0.06);
        --shadow: 0 10px 30px rgba(0,0,0,0.04);
        --shadow-h: 0 20px 40px rgba(0,136,204,0.1);
    }

    /* ========== 全局 ========== */
    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
        color: var(--text) !important;
        background: var(--bg) !important;
    }
    .stApp { max-width: 100%; }
    .main > div { padding-top: 3rem !important; }

    /* ========== 标题 ========== */
    h1, h2, h3 {
        color: #0f172a !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    .stMarkdown h1 { font-size: 2rem; }
    .stMarkdown h2 { font-size: 1.5rem; }
    .stMarkdown h3 { font-size: 1.2rem; }

    /* ========== 侧边栏 ========== */
    section[data-testid="stSidebar"] {
        background: var(--bg-alt) !important;
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text2) !important;
        font-weight: 500 !important;
        border-radius: 10px !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }
    section[data-testid="stSidebar"] .st-emotion-cache-16idsys {
        background: linear-gradient(180deg, var(--primary), var(--primary-dark)) !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
    }

    /* ========== 按钮统一样式 ========== */
    .stButton button, button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    /* 主按钮 - 蓝色渐变 */
    button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 8px 24px rgba(0, 136, 204, 0.15) !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 12px 32px rgba(0, 136, 204, 0.25) !important;
        transform: translateY(-2px) !important;
    }
    /* 次要按钮 - 轮廓风格 */
    button[kind="secondary"], button[data-testid="baseButton-secondary"] {
        background: white !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
    }
    button[kind="secondary"]:hover, button[data-testid="baseButton-secondary"]:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }

    /* 底部操作按钮 - 精确颜色覆盖 */
    [data-testid="stAppViewBlockContainer"] [data-testid="stHorizontalBlock"]:last-of-type
    [data-testid="column"]:nth-child(2) button[data-testid="baseButton-secondary"] {
        background: linear-gradient(135deg, #f44336, #d32f2f) !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stAppViewBlockContainer"] [data-testid="stHorizontalBlock"]:last-of-type
    [data-testid="column"]:nth-child(2) button[data-testid="baseButton-secondary"]:hover {
        box-shadow: 0 12px 32px rgba(244, 67, 54, 0.25) !important;
        transform: translateY(-2px) !important;
    }
    [data-testid="stAppViewBlockContainer"] [data-testid="stHorizontalBlock"]:last-of-type
    [data-testid="column"]:nth-child(3) [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #2196F3, #1976D2) !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stAppViewBlockContainer"] [data-testid="stHorizontalBlock"]:last-of-type
    [data-testid="column"]:nth-child(3) [data-testid="stDownloadButton"] button:hover {
        box-shadow: 0 12px 32px rgba(33, 150, 243, 0.25) !important;
        transform: translateY(-2px) !important;
    }

    /* ========== 标签页 (Tabs) ========== */
    .stTabs [role="tablist"] {
        gap: 4px;
        border-bottom: 1px solid var(--border);
    }
    .stTabs [role="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        color: var(--text2) !important;
        transition: all 0.3s !important;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
    }
    .stTabs [role="tab"]:hover {
        color: var(--primary) !important;
        background: rgba(0, 136, 204, 0.04) !important;
    }

    /* ========== 卡片/容器 ========== */
    div[data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        margin-bottom: 0.5rem;
        box-shadow: var(--shadow);
        transition: all 0.3s;
    }
    div[data-testid="stExpander"]:hover {
        box-shadow: var(--shadow-h);
    }
    div[data-testid="stExpander"] > details {
        border-radius: 16px;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-radius: 16px !important;
    }
    /* 带边框的 container */
    .stContainer [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-radius: 20px !important;
        padding: 1.5rem !important;
        box-shadow: var(--shadow);
    }

    /* ========== 输入框（统一样式） ========== */
    .stTextInput input {
        border: 1px solid #d0d5dd !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        transition: all 0.2s !important;
    }
    .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(0, 136, 204, 0.12) !important;
    }
    /* 输入框标签样式统一 */
    .stTextInput label {
        font-weight: 500 !important;
        color: #475569 !important;
        font-size: 0.85rem !important;
    }
    /* "开始研究"按钮与输入框顶部对齐 */
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"]:first-of-type
    [data-testid="column"]:nth-child(3) .stButton {
        margin-top: 1.8rem !important;
    }

    /* ========== 原始资料卡片 ========== */
    .source-item {
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        border-left: 3px solid var(--primary);
        border-radius: 0 12px 12px 0;
        background: var(--bg-alt);
        transition: all 0.3s;
    }
    .source-item:hover {
        background: white;
        box-shadow: var(--shadow);
        transform: translateX(4px);
    }
    .source-item a {
        color: var(--primary) !important;
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
        color: var(--text3);
    }

    /* ========== 报告标题样式 ========== */
    .report-header {
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #0f172a;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 1.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid var(--primary);
        color: #0f172a;
    }

    /* ========== 进度条美化 ========== */
    div[data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, var(--primary), var(--accent)) !important;
        border-radius: 10px !important;
    }

    /* ========== 提示/信息框 ========== */
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
        box-shadow: var(--shadow);
    }
    div[data-testid="stInfo"] {
        background: rgba(0, 136, 204, 0.06) !important;
        border-left: 3px solid var(--primary) !important;
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
    if "_confirm_delete" not in st.session_state:
        st.session_state._confirm_delete = False
    if "_pending_uploaded" not in st.session_state:
        st.session_state._pending_uploaded = []
    if "_pending_urls" not in st.session_state:
        st.session_state._pending_urls = ""



init_session()


def import_pending_sources(industry_id: int):
    """将暂存的上传文件和链接导入知识库"""
    import tempfile, os, asyncio
    from src.collector.doc_parser import DocParser
    from src.collector.link_importer import LinkImporter

    kb = st.session_state.kb
    parser = DocParser()

    # 处理上传文件
    for uploaded in st.session_state._pending_uploaded:
        try:
            suffix = Path(uploaded.name).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            item = parser.parse_file(tmp_path)
            if item and item.get("content") and len(item["content"]) > 20:
                item["title"] = uploaded.name
                kb.add_source(industry_id, item)
            os.unlink(tmp_path)
        except Exception as e:
            st.warning(f"文件 {uploaded.name} 解析失败: {e}")

    # 处理链接
    urls_text = st.session_state._pending_urls
    if urls_text:
        urls = [u.strip() for u in urls_text.split("\n") if u.strip()]
        if urls:
            importer = LinkImporter()
            try:
                loop = asyncio.get_running_loop()
                items = loop.run_until_complete(importer.import_links(urls))
            except RuntimeError:
                items = asyncio.run(importer.import_links(urls))
            for item in items:
                kb.add_source(industry_id, item)

    # 清空暂存
    st.session_state._pending_uploaded = []
    st.session_state._pending_urls = ""


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

        # Step 1.5 - 导入本地文档和链接
        if st.session_state._pending_uploaded or st.session_state._pending_urls.strip():
            progress_bar.progress(15, text="导入本地资料...")
            import_pending_sources(industry_id)

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
    st.title("📊 AI-Research")
    st.caption("行业研究报告自动生成系统")
    st.divider()

    # ---- 历史行业列表 ----
    st.subheader("📂 历史行业")

    if st.button("➕ 添加新的研究报告", use_container_width=True, type="secondary"):
        st.session_state.current_industry_id = None
        st.session_state.report_content = None
        st.rerun()

    industries = st.session_state.kb.get_industries()
    if industries:
        for ind in industries:
            reports = st.session_state.kb.get_reports(ind["id"])
            date_str = reports[0]["created_at"][:10] if reports else \
                       ind.get("updated_at", "")[:10] or "无记录"

            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"📋 {ind['name']}", key=f"ind_{ind['id']}", use_container_width=True):
                    st.session_state.current_industry_id = ind["id"]
                    reports = st.session_state.kb.get_reports(ind["id"])
                    st.session_state.report_content = reports[0]["content"] if reports else None
                    st.rerun()
            with col2:
                st.caption(date_str)
    else:
        st.info("暂无历史行业，请新建研究")

    st.divider()
    st.caption("v0.1.0 | AI-Research")


# ==================== 主界面 ====================

# --- 新建研究区域（仅当没有正在查看的历史报告时才显示） ---
if st.session_state.current_industry_id is None:
    st.title("🔬 AI 行业研究助手")
    st.markdown("输入行业主题，自动完成 **信息采集 → 知识库构建 → 报告生成** 全流程")

    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 3, 2])
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

    with st.expander("🔍 高级搜索词设置（可选）"):
        search_queries = st.text_area(
            "自定义搜索词（每行一个，为空则自动生成）",
            placeholder=f"{industry_name}\n{industry_name} 最新政策\n{industry_name} 市场规模",
            height=80,
        )

    with st.expander("📄 导入本地文档（可选）"):
        uploaded_files = st.file_uploader(
            "上传 PDF / Word / Markdown / TXT 文件",
            type=["pdf", "docx", "doc", "md", "txt"],
            accept_multiple_files=True,
            key="new_upload_files",
        )
        import_urls = st.text_area(
            "或输入文章链接（每行一个）",
            placeholder="https://example.com/article1\nhttps://example.com/article2",
            height=60,
            key="new_import_urls",
        )
        if st.button("暂存导入资料", use_container_width=True, key="new_import_btn"):
            st.session_state._pending_uploaded = list(uploaded_files) if uploaded_files else []
            st.session_state._pending_urls = import_urls or ""
            if st.session_state._pending_uploaded or st.session_state._pending_urls.strip():
                st.success(f"✅ 已暂存 {len(st.session_state._pending_uploaded)} 个文件和 "
                           f"{len([u for u in st.session_state._pending_urls.split(chr(10)) if u.strip()])} 个链接，开始研究时将自动导入")
            else:
                st.info("请先上传文件或输入链接")

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

# ==================== 查看历史行业 ====================
if st.session_state.current_industry_id is not None:
    industry = st.session_state.kb.get_industry(st.session_state.current_industry_id)
    if industry:
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            st.markdown(f"### 🏭 {industry['name']}")
        with col2:
            current_focus = [f.strip() for f in industry.get("focus", "").split(",") if f.strip()]
            focus = st.multiselect(
                "🎯 关注方向",
                options=config.FOCUS_OPTIONS,
                default=current_focus,
                key=f"edit_focus_{industry['id']}",
                label_visibility="collapsed",
            )
        with col3:
            regen_btn = st.button("📝 重新生成", use_container_width=True,
                                  key="regen_report", type="primary")

        if regen_btn:
            focus_str = ", ".join(focus)
            workflow = st.session_state.workflow
            industry_id = st.session_state.current_industry_id
            # 更新关注方向
            workflow.kb.create_industry(industry["name"], focus_str)
            # 仅重新生成报告
            report_result = workflow.generate_report(industry_id)
            st.session_state.report_content = report_result.get("content", "")
            st.success("✅ 报告已重新生成！")
            st.rerun()

# ==================== 显示报告和知识库 ====================
tab1, tab2, tab3 = st.tabs(["📝 研究报告", "📚 知识库", "📡 原始资料"])

with tab1:
    if st.session_state.report_content:
        st.markdown(st.session_state.report_content, unsafe_allow_html=True)
    elif st.session_state.current_industry_id:
        reports = st.session_state.kb.get_reports(st.session_state.current_industry_id)
        if reports:
            st.session_state.report_content = reports[0]["content"]
            st.markdown(reports[0]["content"], unsafe_allow_html=True)
        else:
            st.info("💡 请先运行「开始研究」生成报告")
    else:
        st.info("💡 在侧边栏选择一个行业，或在输入框填写行业名称后点击「开始研究」")

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

with tab3:
    if st.session_state.current_industry_id:
        sources = st.session_state.kb.get_sources(st.session_state.current_industry_id)
        if sources:
            # URL 去重
            seen = set()
            unique = []
            for s in sources:
                url = s.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                unique.append(s)
            st.caption(f"共 {len(unique)} 条原始资料（去重前 {len(sources)} 条）")
            for s in unique:
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

# 底部（历史行业：搜索词 + 文档导入 + 更新 + 下载）
if st.session_state.current_industry_id is not None:
    st.divider()

    with st.expander("🔍 高级搜索词设置（可选）"):
        history_search_q = st.text_area(
            "自定义搜索词（每行一个，为空则自动生成）",
            placeholder="新能源汽车\n新能源汽车 政策\n新能源汽车 融资",
            height=80,
            key="history_search_queries",
        )

    with st.expander("📄 导入本地文档（可选）"):
        history_uploaded = st.file_uploader(
            "上传 PDF / Word / Markdown / TXT 文件",
            type=["pdf", "docx", "doc", "md", "txt"],
            accept_multiple_files=True,
            key="history_upload",
        )
        history_urls = st.text_area(
            "或输入文章链接（每行一个）",
            placeholder="https://example.com/article1",
            height=60,
            key="history_import_urls",
        )
        if st.button("暂存导入资料", use_container_width=True, key="history_import_btn"):
            st.session_state._pending_uploaded = list(history_uploaded) if history_uploaded else []
            st.session_state._pending_urls = history_urls or ""
            if st.session_state._pending_uploaded or st.session_state._pending_urls.strip():
                st.success(f"✅ 已暂存 {len(st.session_state._pending_uploaded)} 个文件和 "
                           f"{len([u for u in st.session_state._pending_urls.split(chr(10)) if u.strip()])} 个链接")
            else:
                st.info("请先上传文件或输入链接")

    col_left, col_mid, col_right = st.columns([2, 2, 3])
    with col_left:
        if st.button("🔄 更新研究", type="primary", use_container_width=True, key="update_research_bottom"):
            industry = st.session_state.kb.get_industry(st.session_state.current_industry_id)
            if industry:
                with st.spinner("正在更新研究（重新采集 → 构建知识库 → 生成报告）..."):
                    # 先导入本地资料
                    if st.session_state._pending_uploaded or st.session_state._pending_urls.strip():
                        import_pending_sources(st.session_state.current_industry_id)
                    import asyncio
                    workflow = st.session_state.workflow
                    industry_id = st.session_state.current_industry_id

                    # 自定义搜索词
                    queries_list = None
                    if history_search_q:
                        qs = [q.strip() for q in history_search_q.split("\n") if q.strip()]
                        if qs:
                            queries_list = qs

                    try:
                        loop = asyncio.get_running_loop()
                        collect_result = loop.run_until_complete(
                            workflow.run_collection(industry_id, queries_list))
                    except RuntimeError:
                        collect_result = asyncio.run(workflow.run_collection(industry_id, queries_list))

                    workflow.build_knowledge_base(industry_id)
                    report_result = workflow.generate_report(industry_id)
                    st.session_state.report_content = report_result.get("content", "")
                    st.success("✅ 研究已更新！")
                    st.rerun()

    with col_mid:
        if st.button("🗑️ 删除该研究", use_container_width=True, key="delete_industry"):
            st.session_state._confirm_delete = True
            st.rerun()

        if st.session_state.get("_confirm_delete"):
            industry = st.session_state.kb.get_industry(st.session_state.current_industry_id)
            st.warning(f"⚠️ 确定要删除「{industry['name']}」的所有数据吗？此操作不可恢复。")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("是的，确认删除", use_container_width=True, key="confirm_delete"):
                    import shutil
                    industry_id = st.session_state.current_industry_id
                    # 用 workflow 自身的 vector_store 删除集合，保持引用有效
                    st.session_state.workflow.vector_store.delete_collection()
                    st.session_state.kb.delete_industry(industry_id)
                    st.session_state.current_industry_id = None
                    st.session_state.report_content = None
                    st.session_state._confirm_delete = False
                    if industry:
                        report_path = config.REPORTS_DIR / industry["name"]
                        if report_path.exists():
                            shutil.rmtree(report_path, ignore_errors=True)
                    st.success("✅ 已删除！")
                    st.rerun()
            with col_b:
                if st.button("取消", use_container_width=True, key="cancel_delete"):
                    st.session_state._confirm_delete = False
                    st.rerun()

    with col_right:
        if st.session_state.report_content:
            import markdown as md_lib
            html_content = md_lib.markdown(st.session_state.report_content, extensions=["extra"])
            wrap_html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>行业研究报告</title><style>
body {{ max-width:960px; margin:0 auto; padding:40px 20px; font-family:'Inter','PingFang SC','Microsoft YaHei',sans-serif; line-height:1.8; color:#1e293b; }}
h1 {{ font-size:2rem; font-weight:800; color:#0f172a; border-bottom:3px solid #0088cc; padding-bottom:12px; }}
h2 {{ font-size:1.4rem; font-weight:700; color:#0f172a; margin-top:2rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px; }}
</style></head><body>{html_content}</body></html>"""
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button("📥 Markdown", data=st.session_state.report_content,
                    file_name=f"行业研究报告_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown", use_container_width=True, key="download_md")
            with dl2:
                st.download_button("📄 HTML", data=wrap_html,
                    file_name=f"行业研究报告_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html", use_container_width=True, key="download_html")
