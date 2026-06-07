"""全局配置模块"""

import os

# 修复 protobuf 与 chromadb 的兼容性问题
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
CHROMA_DIR = ROOT_DIR / "chroma_db"

# 确保目录存在
for d in [DATA_DIR, REPORTS_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# SQLite 数据库路径
DB_PATH = DATA_DIR / "knowledge.db"

# LLM 配置
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Embedding 配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# 搜索引擎
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

# ChromaDB 集合名
COLLECTION_NAME = "knowledge_base"

# 报告默认设置
DEFAULT_REPORT_TYPE = "周报"
REPORT_SECTIONS = [
    "行业概览",
    "本周核心摘要",
    "重要事件",
    "趋势判断",
    "重点公司动态",
    "机会与风险",
    "战略建议",
    "信息来源",
]

FOCUS_OPTIONS = ["政策", "市场", "公司", "技术", "融资", "风险"]
