"""
Document Repository — Concrete SQLite implementation of IDocumentRepository.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Sequence

from kryntis.repositories.base import IDocumentRepository
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class SQLiteDocumentRepository(IDocumentRepository):
    """
    SQLite-backed Document Repository adhering to SOLID principles.
    """

    def __init__(self, db_path: str = "data/documents.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    mime_type TEXT,
                    created_at REAL NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_id)"
            )
            conn.commit()

    async def get_by_id(self, entity_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT doc_id, source_id, source_path, chunk_index, text, mime_type, created_at, metadata FROM documents WHERE doc_id = ?",
                (entity_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "doc_id": row[0],
                "source_id": row[1],
                "source_path": row[2],
                "chunk_index": row[3],
                "text": row[4],
                "mime_type": row[5],
                "created_at": row[6],
                "metadata": json.loads(row[7]) if row[7] else {},
            }

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT doc_id, source_id, source_path, chunk_index, text, mime_type, created_at, metadata FROM documents LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [
                {
                    "doc_id": r[0],
                    "source_id": r[1],
                    "source_path": r[2],
                    "chunk_index": r[3],
                    "text": r[4],
                    "mime_type": r[5],
                    "created_at": r[6],
                    "metadata": json.loads(r[7]) if r[7] else {},
                }
                for r in cur.fetchall()
            ]

    async def save(self, entity: dict) -> dict:
        doc_id = entity.get("doc_id") or entity.get("chunk_id") or str(time.time_ns())
        source_id = entity.get("source_id", "unknown")
        source_path = entity.get("source_path", "")
        chunk_index = entity.get("chunk_index", 0)
        text = entity.get("text", "")
        mime_type = entity.get("mime_type", "text/plain")
        created_at = entity.get("created_at", time.time())
        metadata = entity.get("metadata", {})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (doc_id, source_id, source_path, chunk_index, text, mime_type, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    source_id,
                    source_path,
                    chunk_index,
                    text,
                    mime_type,
                    created_at,
                    json.dumps(metadata),
                ),
            )
            conn.commit()

        entity["doc_id"] = doc_id
        return entity

    async def delete(self, entity_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM documents WHERE doc_id = ?", (entity_id,))
            conn.commit()
            return cur.rowcount > 0

    async def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM documents")
            row = cur.fetchone()
            return row[0] if row else 0

    async def search_by_text(self, query: str, limit: int = 10) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT doc_id, source_id, source_path, chunk_index, text, mime_type, created_at, metadata FROM documents WHERE text LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            )
            return [
                {
                    "doc_id": r[0],
                    "source_id": r[1],
                    "source_path": r[2],
                    "chunk_index": r[3],
                    "text": r[4],
                    "mime_type": r[5],
                    "created_at": r[6],
                    "metadata": json.loads(r[7]) if r[7] else {},
                }
                for r in cur.fetchall()
            ]

    async def get_by_source_id(self, source_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT doc_id, source_id, source_path, chunk_index, text, mime_type, created_at, metadata FROM documents WHERE source_id = ? ORDER BY chunk_index ASC",
                (source_id,),
            )
            return [
                {
                    "doc_id": r[0],
                    "source_id": r[1],
                    "source_path": r[2],
                    "chunk_index": r[3],
                    "text": r[4],
                    "mime_type": r[5],
                    "created_at": r[6],
                    "metadata": json.loads(r[7]) if r[7] else {},
                }
                for r in cur.fetchall()
            ]
