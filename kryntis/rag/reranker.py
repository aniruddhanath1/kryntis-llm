"""
Cross-encoder reranker for top-K results.

After hybrid retrieval, the reranker scores each (query, chunk) pair
with a cross-encoder model and re-sorts the candidate list.
Falls back to identity (no-op) if cross-encoder not available.
"""

from __future__ import annotations

import asyncio

from kryntis.rag.retriever import RetrievalResult
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    """
    Cross-encoder reranker.

    Uses a small cross-encoder model (~66 MB) to rescore top-K
    retrieval candidates. Falls back to score-order if model
    is not installed.
    """

    def __init__(self) -> None:
        self._model = None
        self._available = False
        self._try_load()

    def _try_load(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(_CROSS_ENCODER_MODEL)
            self._available = True
            log.info("reranker_loaded", model=_CROSS_ENCODER_MODEL)
        except Exception as e:
            log.warning("reranker_unavailable", error=str(e), fallback="score_order")

    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """
        Rerank retrieval results using cross-encoder scores.

        Args:
            query: The user query.
            results: Candidate results from hybrid retriever.

        Returns:
            Reranked list (best first).
        """
        if not self._available or not results:
            return results

        pairs = [(query, r.text) for r in results]
        scores = self._model.predict(pairs)
        for result, score in zip(results, scores):
            result.score = float(score)

        results.sort(key=lambda r: r.score, reverse=True)
        log.debug("reranked", count=len(results))
        return results

    async def arerank(
        self, query: str, results: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.rerank, query, results)
