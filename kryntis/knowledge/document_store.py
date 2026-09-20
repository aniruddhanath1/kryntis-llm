"""
Document Store — SQLite-backed metadata and chunk registry.

Stores all chunk metadata (text, source, provenance, confidence,
timestamps, versioning) separately from the vector index so that
rich metadata queries can be done without touching the vector DB.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterator

from kryntis.chunking.base import Chunk
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS sources (
    source_id       TEXT PRIMARY KEY,
    source_path     TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    file_size_bytes INTEGER,
    mime_type       TEXT,
    added_at        REAL NOT NULL,
    updated_at      REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    metadata        TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    source_path     TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    total_chunks    INTEGER NOT NULL DEFAULT 0,
    text            TEXT NOT NULL,
    page            INTEGER,
    section         TEXT,
    chunk_type      TEXT NOT NULL DEFAULT 'text',
    language        TEXT DEFAULT 'en',
    token_count     INTEGER,
    parent_id       TEXT,
    confidence      REAL NOT NULL DEFAULT 1.0,
    validated       INTEGER NOT NULL DEFAULT 1,
    provenance      TEXT NOT NULL DEFAULT 'document',
    added_at        REAL NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type   ON chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_added  ON chunks(added_at);

CREATE TABLE IF NOT EXISTS knowledge_snapshots (
    snapshot_id     TEXT PRIMARY KEY,
    created_at      REAL NOT NULL,
    description     TEXT,
    chunk_count     INTEGER
);
"""


class DocumentStore:
    """
    SQLite document and chunk metadata store.

    All vector-stored chunks have a corresponding record here
    with full provenance, confidence, and validation status.
    """

    def __init__(self, db_path: str | None = None) -> None:
        cfg = get_config().knowledge
        path = db_path or cfg.sqlite_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._init_db()
        log.info("document_store_init", path=path)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self._path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init_db(self) -> None:
        with self._conn() as con:
            con.executescript(_DDL)

    # ── Sources ───────────────────────────────────────────────────────────────

    def upsert_source(
        self,
        source_id: str,
        source_path: str,
        file_name: str,
        file_size: int = 0,
        mime_type: str = "",
        metadata: dict | None = None,
    ) -> None:
        now = time.time()
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO sources(source_id,source_path,file_name,file_size_bytes,
                    mime_type,added_at,updated_at,metadata)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    metadata=excluded.metadata
                """,
                (
                    source_id, source_path, file_name, file_size, mime_type,
                    now, now, json.dumps(metadata or {}),
                ),
            )

    def list_sources(self) -> list[dict]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM sources WHERE status='active'").fetchall()
        return [dict(r) for r in rows]

    def delete_source(self, source_id: str) -> None:
        with self._conn() as con:
            con.execute("UPDATE sources SET status='deleted' WHERE source_id=?", (source_id,))

    # ── Chunks ────────────────────────────────────────────────────────────────

    def upsert_chunk(
        self,
        chunk: Chunk,
        confidence: float = 1.0,
        validated: bool = True,
        provenance: str = "document",
    ) -> None:
        now = time.time()
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO chunks(chunk_id,source_id,source_path,chunk_index,total_chunks,
                    text,page,section,chunk_type,language,token_count,parent_id,
                    confidence,validated,provenance,added_at,metadata)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    text=excluded.text,
                    confidence=excluded.confidence,
                    validated=excluded.validated,
                    metadata=excluded.metadata
                """,
                (
                    chunk.chunk_id, chunk.source_id, chunk.source_path,
                    chunk.chunk_index, chunk.total_chunks, chunk.text,
                    chunk.page, chunk.section, chunk.chunk_type,
                    chunk.language, chunk.token_count, chunk.parent_id,
                    confidence, int(validated), provenance,
                    now, json.dumps(chunk.metadata),
                ),
            )

    def get_chunk(self, chunk_id: str) -> dict | None:
        with self._conn() as con:
            row = con.execute("SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return dict(row) if row else None

    def get_chunks_by_source(self, source_id: str) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM chunks WHERE source_id=? ORDER BY chunk_index",
                (source_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_chunks_by_source(self, source_id: str) -> int:
        with self._conn() as con:
            cur = con.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
        return cur.rowcount

    def search_by_text(self, query: str, limit: int = 20) -> list[dict]:
        """Simple FTS fallback using LIKE (vector search is primary)."""
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM chunks WHERE text LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def count_chunks(self) -> int:
        with self._conn() as con:
            return con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def record_snapshot(self, snapshot_id: str, description: str = "") -> None:
        count = self.count_chunks()
        with self._conn() as con:
            con.execute(
                "INSERT INTO knowledge_snapshots VALUES(?,?,?,?)",
                (snapshot_id, time.time(), description, count),
            )

    def list_snapshots(self) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM knowledge_snapshots ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


SQLiteDocumentStore = DocumentStore
