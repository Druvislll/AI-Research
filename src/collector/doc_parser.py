"""文档解析器 - 支持 PDF / Word / Markdown / TXT"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional


class DocParser:
    """解析本地导入的各类文档"""

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """解析 PDF 文件"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            return text.strip()
        except ImportError:
            return "PDF 解析需要安装 PyMuPDF: pip install PyMuPDF"
        except Exception as e:
            return f"PDF 解析失败: {e}"

    @staticmethod
    def parse_docx(file_path: str) -> str:
        """解析 Word 文档"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return "Word 解析需要安装 python-docx: pip install python-docx"
        except Exception as e:
            return f"Word 解析失败: {e}"

    @staticmethod
    def parse_markdown(file_path: str) -> str:
        """解析 Markdown 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def parse_txt(file_path: str) -> str:
        """解析纯文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def parse_file(self, file_path: str) -> Optional[dict]:
        """自动识别并解析文件"""
        path = Path(file_path)
        if not path.exists():
            return None

        suffix = path.suffix.lower()
        parsers = {
            ".pdf": self.parse_pdf,
            ".docx": self.parse_docx,
            ".doc": self.parse_docx,
            ".md": self.parse_markdown,
            ".markdown": self.parse_markdown,
            ".txt": self.parse_txt,
        }

        parser = parsers.get(suffix)
        if not parser:
            return None

        content = parser(str(path))
        return {
            "id": hashlib.md5(file_path.encode()).hexdigest(),
            "title": path.stem,
            "url": str(path),
            "content": content[:50000],
            "source_type": "document",
            "file_type": suffix,
            "scraped_at": datetime.now().isoformat(),
        }
