"""文本分块器 - 支持滑动窗口 + 父子分块"""

import re


class TextSplitter:
    """基础分块器：段落合并 + 滑动窗口 + 重叠"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[str]:
        if not text:
            return []
        paragraphs = re.split(r"\n\s*\n", text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        chunks = []
        buf = ""
        for para in paragraphs:
            if len(para) > self.chunk_size:
                if buf:
                    chunks.append(buf)
                    buf = ""
                chunks.extend(self._window_split(para))
                continue
            if buf and len(buf) + len(para) + 2 > self.chunk_size:
                chunks.append(buf)
                buf = self._take_overlap(chunks[-1])
            buf = (buf + "\n\n" + para).strip() if buf else para
        if buf:
            chunks.append(buf)
        return chunks

    def _window_split(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text.strip()]
        chunks = []
        cursor = 0
        while cursor < len(text):
            end = min(cursor + self.chunk_size, len(text))
            if end < len(text):
                ae = self._find_break(text, end)
                if ae > cursor:
                    end = ae
            chunks.append(text[cursor:end].strip())
            if end >= len(text):
                break
            cursor = end - self.chunk_overlap
            if cursor < 0:
                cursor = 0
        return chunks

    @staticmethod
    def _find_break(text: str, anchor: int) -> int:
        search_start = max(anchor - 60, 0)
        for pos in range(anchor - 1, search_start - 1, -1):
            ch = text[pos]
            if ch == '\n':
                return pos + 1
            if ch in '。！？!?':
                return pos + 1
        search_end = min(anchor + 30, len(text))
        for pos in range(anchor, search_end):
            ch = text[pos]
            if ch == '\n':
                return pos + 1
            if ch in '。！？!?':
                return pos + 1
        return anchor

    @staticmethod
    def _take_overlap(chunk: str, overlap: int = 200) -> str:
        if len(chunk) <= overlap:
            return chunk
        target = len(chunk) - overlap
        for pos in range(target, len(chunk)):
            if pos == 0:
                break
            if chunk[pos - 1] in '。！？.!?\n':
                return chunk[pos:].strip()
        for pos in range(target - 1, max(target - 40, 0) - 1, -1):
            if pos == 0:
                break
            if chunk[pos - 1] in '。！？.!?\n':
                return chunk[pos:].strip()
        return chunk[target:].strip()


class ParentChildSplitter:
    """父子分块器

    父块（大块）：提供完整上下文，供 LLM 使用
    子块（小块）：精确检索，供向量搜索使用

    搜索时命中小块 → 返回所属父块作为上下文，
    兼顾检索精度和上下文完整性。
    """

    def __init__(
        self,
        parent_size: int = 1000,
        parent_overlap: int = 200,
        child_size: int = 250,
        child_overlap: int = 50,
    ):
        self.parent_splitter = TextSplitter(chunk_size=parent_size, chunk_overlap=parent_overlap)
        self.child_splitter = TextSplitter(chunk_size=child_size, chunk_overlap=child_overlap)

    def split_text(self, text: str) -> list[dict]:
        """返回 [(parent_text, [child_text, ...]), ...]"""
        parents = self.parent_splitter.split_text(text)
        result = []
        for pt in parents:
            children = self.child_splitter.split_text(pt)
            if not children:
                children = [pt]
            result.append({"parent": pt, "children": children})
        return result
