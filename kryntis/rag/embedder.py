"""
RAG Embedder — dense vector embeddings via sentence-transformers.

Wraps all-MiniLM-L6-v2 (~80 MB) with:
- LRU embedding cache to avoid re-embedding duplicates
- Batch processing with configurable batch size
- Async executor wrapper for non-blocking calls
"""

from __future__ import annotations

import asyncio
from cachetools import LRUCache
from functools import lru_cache
from typing import Sequence

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class Embedder:
    """
    Dense text embedder using sentence-transformers.

    Thread-safe for use in async FastAPI endpoints via executor.
    """

    def __init__(self, model_name: str | None = None) -> None:
        cfg = get_config()
        self._model_name = model_name or cfg.rag.embedder_model
        self._batch_size = cfg.rag.embedder_batch_size
        self._cache: LRUCache = LRUCache(maxsize=cfg.cache.embedding_cache_size)
        self._model = None  # Lazy load

    def _load(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        log.info("embedder_loading", model=self._model_name)
        self._model = SentenceTransformer(self._model_name)
        log.info("embedder_loaded", model=self._model_name, dim=self.embedding_dim)

    @property
    def embedding_dim(self) -> int:
        self._load()
        return self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts synchronously.

        Uses LRU cache for repeated texts.
        Returns list of float vectors.
        """
        self._load()
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            if text in self._cache:
                results[i] = self._cache[text]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            vecs = self._model.encode(
                uncached_texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            ).tolist()
            for idx, vec, text in zip(uncached_indices, vecs, uncached_texts):
                self._cache[text] = vec
                results[idx] = vec

        return results  # type: ignore

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        """Async wrapper — runs embedding in thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, texts)

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    async def aembed_one(self, text: str) -> list[float]:
        vecs = await self.aembed([text])
        return vecs[0]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Return the singleton Embedder instance."""
    return Embedder()
