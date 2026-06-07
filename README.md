# AI-Research

行业研究报告自动生成系统。输入行业主题，自动完成 **信息采集 → 知识库构建 → 报告生成** 全流程。

## 功能

- 多源信息采集（搜索引擎 + 网页抓取 + 文档导入 + 链接导入）
- 父子分块知识库（ChromaDB 向量检索 + SQLite 元数据管理）
- LLM 行业研究报告生成（8 章节结构化报告，含来源引用）
- 重复内容自动去重、增量更新

## 环境要求

| 环境 | 要求 |
|------|------|
| Python | 3.10 |
| 包管理器 | [uv](https://docs.astral.sh/uv/)（推荐）或 pip |
| LLM API | 兼容 OpenAI API 的服务（OpenAI / DeepSeek / 通义千问等） |
| GPU | 可选，NVIDIA 显卡 + CUDA 可加速向量计算 |

## 快速部署

```bash
# 1. 克隆仓库
git clone https://github.com/Druvislll/AI-Research.git
cd AI-Research

# 2. 创建虚拟环境
uv venv --python 3.10 .venv

# 3. 激活环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 4. 安装依赖
uv pip install -r pyproject.toml

# 5. 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填写你的 LLM API Key 和 Base URL

# 6. 启动应用
streamlit run app.py
```

浏览器打开 **http://localhost:8501** 即可使用。

## GPU 加速（可选）

有 NVIDIA 显卡时，安装 CUDA 版 PyTorch 可大幅提升向量嵌入速度：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

验证 GPU 是否生效：

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

## 配置说明

编辑 `.env` 文件：

```ini
# LLM 配置（任选一种）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 或使用 DeepSeek / 通义千问等兼容服务
# DEEPSEEK_API_KEY=sk-xxx
# DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## 项目结构

```
AI-Research/
├── app.py                      # Streamlit 主界面
├── pyproject.toml              # 项目依赖
├── src/
│   ├── config.py               # 全局配置
│   ├── collector/              # 信息采集模块
│   │   ├── web_scraper.py      # 网页内容抓取
│   │   ├── search_collector.py # 搜索引擎搜索
│   │   ├── doc_parser.py       # PDF/Word/MD 解析
│   │   └── link_importer.py    # 链接导入
│   ├── knowledge_base/         # 知识库模块
│   │   ├── models.py           # SQLite 元数据
│   │   ├── vector_store.py     # ChromaDB 向量存储
│   │   ├── retriever.py        # 语义检索
│   │   └── text_splitter.py    # 父子分块器
│   ├── report/                 # 报告生成模块
│   │   ├── generator.py        # LLM 报告生成
│   │   └── templates.py        # 报告模板
│   ├── llm/                    # LLM 客户端
│   │   └── __init__.py
│   └── orchestrator/           # 工作流编排
│       └── workflow.py
├── data/                       # SQLite 数据库（自动生成）
├── chroma_db/                  # ChromaDB 向量库（自动生成）
└── reports/                    # 生成报告（自动生成）
```

## 数据清理

删除以下目录即可重置所有数据：

```bash
rm -rf data/ chroma_db/ reports/
```
