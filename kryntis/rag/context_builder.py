"""
Context Builder — assembles RAG results into a bounded context window.

Takes reranked retrieval results and constructs the context text
injected into the LLM system prompt, respecting token budgets.
"""

from __future__ import annotations

from kryntis.rag.retriever import RetrievalResult
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class ContextBuilder:
    """
    Builds a bounded context string from retrieved chunks.

    Ensures the context never exceeds a configured token budget
    by greedily selecting the highest-scored chunks that fit.
    """

    def __init__(self, max_context_tokens: int | None = None) -> None:
        cfg = get_config()
        # Reserve 40% of context for system prompt + conversation + response
        self._max_tokens = max_context_tokens or int(cfg.model.context_length * 0.4)

    def build(
        self,
        results: list[RetrievalResult],
        include_citations: bool = True,
    ) -> tuple[str, list[dict]]:
        """
        Build context string and citation list.

        Args:
            results: Ranked RetrievalResult list.
            include_citations: Whether to append citation markers.

        Returns:
            (context_text, citations) tuple.
            citations = list of {index, chunk_id, source_path, section, score}
        """
        selected: list[RetrievalResult] = []
        token_budget = self._max_tokens
        approx_tokens_used = 0

        for result in results:
            chunk_tokens = result.metadata.get("token_count") or (len(result.text) // 4)
            if approx_tokens_used + chunk_tokens > token_budget:
                break
            selected.append(result)
            approx_tokens_used += chunk_tokens

        parts: list[str] = []
        citations: list[dict] = []

        for i, result in enumerate(selected, start=1):
            citation_tag = f"[{i}]" if include_citations else ""
            parts.append(f"{citation_tag} {result.text.strip()}")
            citations.append({
                "index": i,
                "chunk_id": result.chunk_id,
                "source_path": result.source_path,
                "section": result.section,
                "score": round(result.score, 4),
            })

        context = "\n\n".join(parts)
        log.debug(
            "context_built",
            chunks_selected=len(selected),
            approx_tokens=approx_tokens_used,
            citations=len(citations),
        )
        return context, citations
