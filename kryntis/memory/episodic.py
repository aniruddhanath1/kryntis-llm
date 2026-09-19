"""
Episodic Memory — session-scoped event records.

Records each conversation session as an episode with summary,
key facts, and outcome. Episodes are stored in SQLite and
can be retrieved to provide cross-session context.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id      TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    started_at      REAL NOT NULL,
    ended_at        REAL,
    summary         TEXT,
    key_facts       TEXT NOT NULL DEFAULT '[]',
    turn_count      INTEGER NOT NULL DEFAULT 0,
    topics          TEXT NOT NULL DEFAULT '[]',
    outcome         TEXT NOT NULL DEFAULT 'completed'
);
CREATE INDEX IF NOT EXISTS idx_ep_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_ep_started ON episodes(started_at);
"""


@dataclass
class Episode:
    """A single conversation session record."""
    episode_id: str
    session_id: str
    started_at: float
    ended_at: float | None = None
    summary: str = ""
    key_facts: list[str] = field(default_factory=list)
    turn_count: int = 0
    topics: list[str] = field(default_factory=list)
    outcome: str = "completed"


class EpisodicMemory:
    """
    Records and retrieves conversation episodes.

    Each user session produces an Episode. Summaries and key facts
    from past episodes are surfaced to the LLM for cross-session continuity.
    """

    def __init__(self, db_path: str | None = None) -> None:
        cfg = get_config()
        self._path = db_path or cfg.knowledge.sqlite_path
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.executescript(_DDL)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self._path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def start_episode(self, session_id: str) -> Episode:
        ep = Episode(
            episode_id=str(uuid.uuid4()),
            session_id=session_id,
            started_at=time.time(),
        )
        with self._conn() as con:
            con.execute(
                "INSERT INTO episodes(episode_id,session_id,started_at,key_facts,topics) VALUES(?,?,?,?,?)",
                (ep.episode_id, ep.session_id, ep.started_at, "[]", "[]"),
            )
        log.debug("episode_started", episode_id=ep.episode_id, session=session_id)
        return ep

    def end_episode(
        self,
        episode_id: str,
        summary: str,
        key_facts: list[str],
        topics: list[str],
        turn_count: int,
    ) -> None:
        with self._conn() as con:
            con.execute(
                """UPDATE episodes SET ended_at=?,summary=?,key_facts=?,topics=?,turn_count=?
                   WHERE episode_id=?""",
                (
                    time.time(), summary,
                    json.dumps(key_facts), json.dumps(topics),
                    turn_count, episode_id,
                ),
            )
        log.info("episode_ended", episode_id=episode_id, turns=turn_count)

    def get_recent_episodes(self, session_id: str, limit: int = 5) -> list[Episode]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM episodes WHERE session_id=? ORDER BY started_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_all_recent(self, limit: int = 10) -> list[Episode]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM episodes ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        return Episode(
            episode_id=row["episode_id"],
            session_id=row["session_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            summary=row["summary"] or "",
            key_facts=json.loads(row["key_facts"] or "[]"),
            turn_count=row["turn_count"],
            topics=json.loads(row["topics"] or "[]"),
            outcome=row["outcome"],
        )
