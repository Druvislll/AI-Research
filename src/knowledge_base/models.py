"""知识库数据模型 - SQLite 元数据管理"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from src import config


class KnowledgeBase:
    """知识库元数据管理（SQLite）"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS industries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                focus TEXT DEFAULT '',
                report_type TEXT DEFAULT '周报',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry_id INTEGER NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                url TEXT DEFAULT '',
                content TEXT DEFAULT '',
                source_type TEXT DEFAULT 'web',
                tags TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                scraped_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (industry_id) REFERENCES industries(id)
            );

            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry_id INTEGER NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                content TEXT DEFAULT '',
                url TEXT DEFAULT '',
                vector_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (industry_id) REFERENCES industries(id)
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                report_type TEXT DEFAULT '周报',
                created_at TEXT NOT NULL,
                FOREIGN KEY (industry_id) REFERENCES industries(id)
            );

            -- 确保唯一约束（兼容旧数据库升级）
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_unique
                ON sources(industry_id, source_id);
        """)
        conn.commit()
        conn.close()

    def create_industry(self, name: str, focus: str = "", report_type: str = "周报") -> int:
        conn = self._get_conn()
        now = datetime.now().isoformat()
        try:
            conn.execute(
                "INSERT INTO industries (name, focus, report_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, focus, report_type, now, now),
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            # 已存在则更新 focus 和 updated_at
            conn.execute(
                "UPDATE industries SET focus = ?, updated_at = ? WHERE name = ?",
                (focus, now, name),
            )
            conn.commit()
            row = conn.execute("SELECT id FROM industries WHERE name = ?", (name,)).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def get_industries(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM industries ORDER BY updated_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_industry(self, industry_id: int) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM industries WHERE id = ?", (industry_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def add_source(self, industry_id: int, item: dict) -> int:
        """添加或更新来源，相同 URL 不重复入库，仅更新内容"""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        try:
            url = item.get("url", "")
            source_id = item.get("id", "")
            title = item.get("title", "")
            content = item.get("content", "")
            source_type = item.get("source_type", "web")
            tags = item.get("tags", "")
            summary = item.get("summary", "")
            scraped_at = item.get("scraped_at", now)

            # URL 级别去重：相同 industry 下相同 URL 只更新不新增
            if url:
                existing = conn.execute(
                    "SELECT id, source_id, created_at FROM sources WHERE industry_id = ? AND url = ?",
                    (industry_id, url),
                ).fetchone()
                if existing:
                    conn.execute(
                        """UPDATE sources SET
                               title = ?, content = ?,
                               source_type = ?, tags = ?, summary = ?,
                               scraped_at = ?
                           WHERE id = ?""",
                        (title, content,
                         source_type, tags, summary,
                         scraped_at, existing["id"]),
                    )
                    conn.commit()
                    conn.close()
                    return existing["id"]

            # 无 URL 或新 URL：用 source_id UPSERT（兼容旧数据）
            conn.execute(
                """INSERT INTO sources
                   (industry_id, source_id, title, url, content, source_type, tags, summary, scraped_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(industry_id, source_id) DO UPDATE SET
                       content = CASE WHEN excluded.content != '' THEN excluded.content ELSE sources.content END,
                       title   = CASE WHEN excluded.title   != '' THEN excluded.title   ELSE sources.title END,
                       url     = excluded.url,
                       scraped_at = excluded.scraped_at""",
                (industry_id, source_id, title, url, content,
                 source_type, tags, summary, scraped_at, now),
            )
            conn.commit()
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.close()
            return row_id
        except Exception as e:
            conn.close()
            return 0

    def get_sources(self, industry_id: int) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM sources WHERE industry_id = ? ORDER BY created_at DESC",
            (industry_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_knowledge_entry(self, industry_id: int, entry: dict) -> int:
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO knowledge_entries
               (industry_id, source_id, title, summary, tags, content, url, vector_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                industry_id,
                entry.get("source_id", ""),
                entry.get("title", ""),
                entry.get("summary", ""),
                entry.get("tags", ""),
                entry.get("content", ""),
                entry.get("url", ""),
                entry.get("vector_id", ""),
                now,
            ),
        )
        conn.commit()
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return row_id

    def get_knowledge_entries(self, industry_id: int) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM knowledge_entries WHERE industry_id = ? ORDER BY created_at DESC",
            (industry_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_report(self, industry_id: int, title: str, content: str, report_type: str = "周报") -> int:
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO reports (industry_id, title, content, report_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (industry_id, title, content, report_type, now),
        )
        conn.commit()
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return row_id

    def get_reports(self, industry_id: int) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM reports WHERE industry_id = ? ORDER BY created_at DESC",
            (industry_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_industry(self, industry_id: int) -> bool:
        """删除行业及其所有关联数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM sources WHERE industry_id = ?", (industry_id,))
            conn.execute("DELETE FROM knowledge_entries WHERE industry_id = ?", (industry_id,))
            conn.execute("DELETE FROM reports WHERE industry_id = ?", (industry_id,))
            conn.execute("DELETE FROM industries WHERE id = ?", (industry_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
