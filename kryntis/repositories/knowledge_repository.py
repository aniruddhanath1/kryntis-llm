"""
Knowledge Repository — Concrete Vector / Semantic implementation of IKnowledgeRepository.
"""

from __future__ import annotations

import math
from typing import Sequence

from kryntis.repositories.base import IKnowledgeRepository
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class InMemoryKnowledgeRepository(IKnowledgeRepository):
    """
    In-memory vector & semantic Knowledge Repository.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict] = {}

    async def get_by_id(self, entity_id: str) -> dict | None:
        return self._records.get(entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[dict]:
        all_items = list(self._records.values())
        return all_items[offset : offset + limit]

    async def save(self, entity: dict) -> dict:
        entity_id = entity.get("id") or entity.get("chunk_id") or str(len(self._records) + 1)
        entity["id"] = entity_id
        self._records[entity_id] = entity
        return entity

    async def delete(self, entity_id: str) -> bool:
        return self._records.pop(entity_id, None) is not None

    async def count(self) -> int:
        return len(self._records)

    async def find_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """Compute cosine similarity against registered embeddings."""
        scored: list[tuple[float, dict]] = []

        for rec in self._records.values():
            emb = rec.get("embedding")
            if not emb or len(emb) != len(query_embedding):
                continue

            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, emb))
            norm_q = math.sqrt(sum(a * a for a in query_embedding))
            norm_e = math.sqrt(sum(b * b for b in emb))

            if norm_q > 0 and norm_e > 0:
                sim = dot / (norm_q * norm_e)
                if sim >= score_threshold:
                    scored.append((sim, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, **r} for s, r in scored[:top_k]]
