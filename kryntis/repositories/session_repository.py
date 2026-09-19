"""
Session Repository — Concrete SQLite implementation of ISessionRepository.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Sequence

from kryntis.repositories.base import ISessionRepository
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class SQLiteSessionRepository(ISessionRepository):
    """
    SQLite-backed Session Repository adhering to SOLID principles.
    """

    def __init__(self, db_path: str = "data/sessions/sessions.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_st_session ON session_turns(session_id, created_at)"
            )
            conn.commit()

    async def get_by_id(self, entity_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT turn_id, session_id, role, content, created_at, metadata FROM session_turns WHERE turn_id = ?",
                (entity_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            return {
                "turn_id": r[0],
                "session_id": r[1],
                "role": r[2],
                "content": r[3],
                "created_at": r[4],
                "metadata": json.loads(r[5]) if r[5] else {},
            }

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT turn_id, session_id, role, content, created_at, metadata FROM session_turns LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [
                {
                    "turn_id": r[0],
                    "session_id": r[1],
                    "role": r[2],
                    "content": r[3],
                    "created_at": r[4],
                    "metadata": json.loads(r[5]) if r[5] else {},
                }
                for r in cur.fetchall()
            ]

    async def save(self, entity: dict) -> dict:
        turn_id = entity.get("turn_id") or str(time.time_ns())
        session_id = entity.get("session_id", "default")
        role = entity.get("role", "user")
        content = entity.get("content", "")
        created_at = entity.get("created_at", time.time())
        metadata = entity.get("metadata", {})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO session_turns (turn_id, session_id, role, content, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (turn_id, session_id, role, content, created_at, json.dumps(metadata)),
            )
            conn.commit()

        entity["turn_id"] = turn_id
        return entity

    async def delete(self, entity_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM session_turns WHERE turn_id = ?", (entity_id,))
            conn.commit()
            return cur.rowcount > 0

    async def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM session_turns")
            row = cur.fetchone()
            return row[0] if row else 0

    async def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> dict:
        entity = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": time.time(),
            "metadata": metadata or {},
        }
        return await self.save(entity)

    async def get_recent_turns(self, session_id: str, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT turn_id, session_id, role, content, created_at, metadata
                FROM session_turns
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
            return [
                {
                    "turn_id": r[0],
                    "session_id": r[1],
                    "role": r[2],
                    "content": r[3],
                    "created_at": r[4],
                    "metadata": json.loads(r[5]) if r[5] else {},
                }
                for r in reversed(rows)
            ]

    async def search_turns(self, session_id: str, query: str, limit: int = 10) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT turn_id, session_id, role, content, created_at, metadata
                FROM session_turns
                WHERE session_id = ? AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, f"%{query}%", limit),
            )
            return [
                {
                    "turn_id": r[0],
                    "session_id": r[1],
                    "role": r[2],
                    "content": r[3],
                    "created_at": r[4],
                    "metadata": json.loads(r[5]) if r[5] else {},
                }
                for r in cur.fetchall()
            ]
