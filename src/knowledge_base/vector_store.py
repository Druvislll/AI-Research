"""向量存储模块 - ChromaDB 语义检索"""

from pathlib import Path
from typing import Optional
import chromadb
from src import config


class VectorStore:
    """ChromaDB 向量存储封装（父子分块）"""

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or config.CHROMA_DIR
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        """添加文档到向量库"""
        if not ids:
            return
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """语义搜索，返回最相关的文档"""
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, 100),
        )
        items = []
        if not results["ids"]:
            return items
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
        return items

    def search_parents(self, query: str, top_k: int = 10) -> list[dict]:
        """语义搜索子块 → 按父块 parent_id 去重 → 返回父块上下文

        这是父子分块的核心检索方法：
        1. 先在子块上做精确语义搜索
        2. 按 parent_id 分组，取每个父块中得分最高的子块
        3. 返回父块完整文本
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k * 3, 100),  # 多搜一些，去重后够用
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        # 按 parent_id 分组，保留得分最高的子块
        parent_map = {}
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            parent_id = meta.get("parent_id", "")
            parent_text = meta.get("parent_text", "")
            distance = results["distances"][0][i] if results["distances"] else 0

            if not parent_id or not parent_text:
                continue

            # 只保留每个父块中得分最高的子块
            if parent_id not in parent_map or distance < parent_map[parent_id]["distance"]:
                parent_map[parent_id] = {
                    "parent_id": parent_id,
                    "parent_text": parent_text,
                    "title": meta.get("title", ""),
                    "url": meta.get("url", ""),
                    "distance": distance,
                }

        # 按得分排序，取 top_k
        sorted_parents = sorted(parent_map.values(), key=lambda x: x["distance"])
        return sorted_parents[:top_k]

    def delete_collection(self) -> None:
        """删除整个集合"""
        self.client.delete_collection(config.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """返回向量库中的文档数量"""
        return self.collection.count()
