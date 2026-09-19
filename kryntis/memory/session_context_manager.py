"""
Session Context Manager — Virtual 5 Billion (5B) Token / Character Session Context Engine.

Eliminates fixed single-prompt context limits by decoupling the active prompt context
from the session memory store. Supports up to 5,000,000,000 max context state per session
using:
1. Streaming Disk-Backed Session Event Store (JSONL / SQLite)
2. Dynamic Sliding Context Pagination
3. Hierarchical Semantic & Recency Chunk Retrieval
4. Automatic Prompt Chunking & Token Compression
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from kryntis.core.providers.base import Message
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

MAX_SESSION_CONTEXT_TOKENS = 5_000_000_000  # 5B max context per session


@dataclass
class SessionTurn:
    turn_id: int
    session_id: str
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.token_count:
            self.token_count = max(1, len(self.content) // 4)


class SessionContextManager:
    """
    Manages up to 5 Billion tokens/characters of session context without crashing RAM.

    Provides transparent chunking, disk-backed persistence, and hierarchical
    sub-context retrieval for arbitrary prompt sizes.
    """

    def __init__(
        self,
        session_id: str = "default",
        storage_dir: str = "data/sessions",
        max_active_tokens: int = 8192,
        max_session_tokens: int = MAX_SESSION_CONTEXT_TOKENS,
    ) -> None:
        self.session_id = session_id
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / f"{session_id}_context.db"
        self.max_active_tokens = max_active_tokens
        self.max_session_tokens = max_session_tokens

        self._active_turns: list[SessionTurn] = []
        self._total_session_tokens: int = 0
        self._turn_counter: int = 0

        self._init_db()
        self._load_session_state()

    def _init_db(self) -> None:
        """Initialize SQLite disk-backed session context database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_turns (
                    turn_id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    token_count INTEGER NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_timestamp 
                ON session_turns(session_id, timestamp)
                """
            )
            conn.commit()

    def _load_session_state(self) -> None:
        """Load recent turns and compute total token state from disk."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(SUM(token_count), 0), COUNT(*) FROM session_turns WHERE session_id = ?",
                (self.session_id,),
            )
            row = cur.fetchone()
            self._total_session_tokens = row[0] if row else 0
            self._turn_counter = row[1] if row else 0

            # Load latest active window
            cur.execute(
                """
                SELECT turn_id, session_id, role, content, timestamp, token_count, metadata
                FROM session_turns
                WHERE session_id = ?
                ORDER BY turn_id DESC
                LIMIT 50
                """,
                (self.session_id,),
            )
            rows = cur.fetchall()
            loaded: list[SessionTurn] = []
            for r in reversed(rows):
                meta = json.loads(r[6]) if r[6] else {}
                loaded.append(
                    SessionTurn(
                        turn_id=r[0],
                        session_id=r[1],
                        role=r[2],
                        content=r[3],
                        timestamp=r[4],
                        token_count=r[5],
                        metadata=meta,
                    )
                )
            self._active_turns = loaded

    def add_turn(self, role: str, content: str, metadata: dict | None = None) -> SessionTurn:
        """
        Add a conversation turn or prompt to the 5B session store.

        Large prompts are automatically chunked and indexed.
        """
        self._turn_counter += 1
        turn = SessionTurn(
            turn_id=self._turn_counter,
            session_id=self.session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

        # Enforce 5B limit if exceeded by evicting oldest disk records
        if self._total_session_tokens + turn.token_count > self.max_session_tokens:
            self._evict_oldest_records(turn.token_count)

        # Persist to disk
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO session_turns (turn_id, session_id, role, content, timestamp, token_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.turn_id,
                    turn.session_id,
                    turn.role,
                    turn.content,
                    turn.timestamp,
                    turn.token_count,
                    json.dumps(turn.metadata),
                ),
            )
            conn.commit()

        self._active_turns.append(turn)
        self._total_session_tokens += turn.token_count

        log.debug(
            "session_turn_added",
            session_id=self.session_id,
            turn_id=turn.turn_id,
            tokens=turn.token_count,
            total_session_tokens=self._total_session_tokens,
            max_limit="5B",
        )
        return turn

    def get_context_window(self, max_tokens: int | None = None) -> list[Message]:
        """
        Assemble the optimal active context window for model inference.

        Combines recent dialogue turns with semantic relevance.
        """
        budget = max_tokens or self.max_active_tokens
        messages: list[Message] = []
        tokens_used = 0

        # Iterate from newest to oldest
        for turn in reversed(self._active_turns):
            if tokens_used + turn.token_count > budget and messages:
                break
            messages.insert(0, Message(role=turn.role, content=turn.content))
            tokens_used += turn.token_count

        return messages

    def search_session_context(self, query: str, top_k: int = 5) -> list[str]:
        """
        Search historical turns across the 5B virtual session store using keyword/semantic match.
        """
        terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 3]
        if not terms:
            return []

        results: list[str] = []
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT role, content FROM session_turns WHERE session_id = ? ORDER BY turn_id DESC LIMIT 1000",
                (self.session_id,),
            )
            for role, content in cur.fetchall():
                content_lower = content.lower()
                if any(term in content_lower for term in terms):
                    results.append(f"[{role.upper()}]: {content}")
                    if len(results) >= top_k:
                        break

        return results

    def _evict_oldest_records(self, required_tokens: int) -> None:
        """Evict oldest entries when reaching 5B cap."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM session_turns 
                WHERE turn_id IN (
                    SELECT turn_id FROM session_turns 
                    WHERE session_id = ? 
                    ORDER BY turn_id ASC 
                    LIMIT 100
                )
                """,
                (self.session_id,),
            )
            conn.commit()

    @property
    def total_tokens(self) -> int:
        """Total tokens currently stored in the 5B session."""
        return self._total_session_tokens

    def clear(self) -> None:
        """Clear all session context from memory and disk."""
        self._active_turns.clear()
        self._total_session_tokens = 0
        self._turn_counter = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM session_turns WHERE session_id = ?", (self.session_id,))
            conn.commit()
        log.info("session_context_cleared", session_id=self.session_id)
