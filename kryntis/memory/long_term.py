"""
Long-term semantic memory — vectorised persistent memory store.

Stores important facts and conversation summaries as embeddings
so they can be retrieved by semantic similarity across sessions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from kryntis.knowledge.vector_store import BaseVectorStore, VectorSearchResult, build_vector_store
from kryntis.rag.embedder import get_embedder
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class MemoryEntry:
    """A single long-term memory item."""
    memory_id: str
    content: str
    source_session: str
    importance: float        # 0.0 → 1.0
    created_at: float
    access_count: int = 0
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class LongTermMemory:
    """
    Persistent semantic memory using the vector store.

    Memories are embedded and stored in a dedicated vector collection
    separate from the document knowledge base.
    """

    def __init__(self, vector_store: BaseVectorStore | None = None) -> None:
        cfg = get_config()
        # Use a separate collection for long-term memories
        from kryntis.knowledge.vector_store import ChromaAdapter
        self._vs = vector_store or ChromaAdapter(
            path=cfg.knowledge.chroma_path,
            collection_name=cfg.memory.long_term_collection,
        )
        self._embedder = get_embedder()

    async def store(
        self,
        content: str,
        session_id: str = "default",
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Store a memory with its embedding.

        Args:
            content: The memory text to store.
            session_id: Session that generated this memory.
            importance: Importance weight [0, 1].
            tags: Optional tag list for filtering.

        Returns:
            The stored MemoryEntry.
        """
        memory_id = str(uuid.uuid4())
        now = time.time()
        embedding = await self._embedder.aembed_one(content)

        self._vs.add(
            ids=[memory_id],
            embeddings=[embedding],
            texts=[content],
            metadatas=[{
                "session_id": session_id,
                "importance": importance,
                "created_at": now,
                "tags": ",".join(tags or []),
            }],
        )
        entry = MemoryEntry(
            memory_id=memory_id,
            content=content,
            source_session=session_id,
            importance=importance,
            created_at=now,
            tags=tags or [],
        )
        log.debug("long_term_memory_stored", memory_id=memory_id, importance=importance)
        return entry

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        min_importance: float = 0.0,
    ) -> list[VectorSearchResult]:
        """
        Retrieve semantically relevant memories.

        Args:
            query: Query to search memories for.
            top_k: Max results.
            min_importance: Minimum importance threshold.

        Returns:
            List of matching VectorSearchResult.
        """
        embedding = await self._embedder.aembed_one(query)
        results = self._vs.search(embedding, top_k=top_k * 2)

        if min_importance > 0:
            results = [
                r for r in results
                if float(r.metadata.get("importance", 0)) >= min_importance
            ]

        log.debug("long_term_recall", query_len=len(query), found=len(results[:top_k]))
        return results[:top_k]

    def delete(self, memory_id: str) -> None:
        self._vs.delete([memory_id])

    def count(self) -> int:
        return self._vs.count()
