"""
pgvector (PostgreSQL Vector) Adapter for Kryntis AI Knowledge Store.

Uses psycopg3 or asyncpg + pgvector extension in PostgreSQL.
"""

from __future__ import annotations

import json
from typing import Any

from kryntis.knowledge.vector_store import BaseVectorStore, VectorSearchResult
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class PGVectorAdapter(BaseVectorStore):
    """
    PostgreSQL + pgvector vector store adapter.

    Requires:
      - PostgreSQL database with `vector` extension enabled (`CREATE EXTENSION IF NOT EXISTS vector;`)
      - `psycopg` (v3) library installed (`pip install "psycopg[binary]"` or `pip install pgvector`)
    """

    def __init__(
        self,
        connection_string: str = "postgresql://postgres:postgres@localhost:5432/kryntis_db",
        table_name: str = "kryntis_vectors",
        vector_dim: int = 384,
    ) -> None:
        try:
            import psycopg
            self._psycopg = psycopg
        except ImportError as e:
            raise ImportError(
                "Install psycopg (v3) for PostgreSQL vector store: pip install \"psycopg[binary]\""
            ) from e

        self._conn_str = connection_string
        self._table = table_name
        self._dim = vector_dim

        self._init_db()
        log.info("pgvector_adapter_init", conn=connection_string, table=table_name, dim=vector_dim)

    def _get_connection(self):
        return self._psycopg.connect(self._conn_str, autocommit=True)

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self._table} (
                        chunk_id VARCHAR(255) PRIMARY KEY,
                        text TEXT NOT NULL,
                        embedding vector({self._dim}),
                        metadata JSONB
                    );
                """)

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for chunk_id, vec, text, meta in zip(ids, embeddings, texts, metadatas):
                    cur.execute(
                        f"""
                        INSERT INTO {self._table} (chunk_id, text, embedding, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata;
                        """,
                        (chunk_id, text, str(vec), json.dumps(meta)),
                    )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        results: list[VectorSearchResult] = []
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Cosine distance operator is <=> in pgvector. Cosine Similarity = 1 - (embedding <=> query_vec)
                cur.execute(
                    f"""
                    SELECT chunk_id, text, metadata, 1 - (embedding <=> %s::vector) AS similarity
                    FROM {self._table}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (str(query_embedding), str(query_embedding), top_k),
                )
                rows = cur.fetchall()
                for row in rows:
                    chunk_id, text, meta, sim = row
                    meta_dict = meta if isinstance(meta, dict) else json.loads(meta or "{}")
                    results.append(
                        VectorSearchResult(
                            chunk_id=chunk_id,
                            text=text,
                            score=float(sim),
                            metadata=meta_dict,
                        )
                    )
        return results

    def delete(self, ids: list[str]) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self._table} WHERE chunk_id = ANY(%s);", (ids,))

    def count(self) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self._table};")
                return cur.fetchone()[0]

    def reset(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self._table};")
