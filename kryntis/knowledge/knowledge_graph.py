"""
Knowledge Graph — lightweight entity/relation store in SQLite.

Tracks key entities extracted from documents and their relationships,
enabling graph-augmented RAG retrieval.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_id   TEXT,
    added_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS relations (
    relation_id TEXT PRIMARY KEY,
    subject_id  TEXT NOT NULL REFERENCES entities(entity_id),
    predicate   TEXT NOT NULL,
    object_id   TEXT NOT NULL REFERENCES entities(entity_id),
    confidence  REAL NOT NULL DEFAULT 0.9,
    source_id   TEXT,
    added_at    REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_rel_subject  ON relations(subject_id);
"""


class KnowledgeGraph:
    """
    Simple entity-relation knowledge graph backed by SQLite.

    Used to augment RAG results with related entities and provide
    graph-based context for complex multi-hop questions.
    """

    def __init__(self, db_path: str | None = None) -> None:
        cfg = get_config().knowledge
        self._path = db_path or cfg.sqlite_path
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.executescript(_DDL)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self._path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def add_entity(self, entity_id: str, name: str, entity_type: str, source_id: str = "") -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO entities VALUES(?,?,?,?,?)",
                (entity_id, name, entity_type, source_id, time.time()),
            )

    def add_relation(
        self,
        relation_id: str,
        subject_id: str,
        predicate: str,
        object_id: str,
        confidence: float = 0.9,
        source_id: str = "",
    ) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO relations VALUES(?,?,?,?,?,?,?)",
                (relation_id, subject_id, predicate, object_id, confidence, source_id, time.time()),
            )

    def get_related(self, entity_id: str, depth: int = 1) -> list[dict]:
        """Return entities related to the given entity."""
        with self._conn() as con:
            rows = con.execute(
                """
                SELECT e.entity_id, e.name, e.entity_type, r.predicate, r.confidence
                FROM relations r
                JOIN entities e ON e.entity_id = r.object_id
                WHERE r.subject_id = ?
                ORDER BY r.confidence DESC
                """,
                (entity_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def find_entity(self, name: str) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM entities WHERE name LIKE ? LIMIT 10",
                (f"%{name}%",),
            ).fetchall()
        return [dict(r) for r in rows]
