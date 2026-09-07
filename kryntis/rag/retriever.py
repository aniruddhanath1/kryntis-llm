"""
RAG Retriever — hybrid dense + sparse retrieval.

Combines:
  - Dense retrieval:  cosine similarity on vector embeddings (FAISS/Chroma)
  - Sparse retrieval: BM25 keyword matching
  - Score fusion:     weighted RRF (Reciprocal Rank Fusion)
"""

from __future__ import annotations

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from kryntis.knowledge.document_store import DocumentStore
from kryntis.knowledge.vector_store import BaseVectorStore, VectorSearchResult, build_vector_store
from kryntis.rag.embedder import Embedder, get_embedder
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class RetrievalResult:
    """A retrieved chunk with fused ranking score."""
    chunk_id: str
    text: str
    score: float
    dense_score: float
    sparse_score: float
    metadata: dict
    source_path: str = ""
    section: str = ""


class HybridRetriever:
    """
    Hybrid retriever combining dense and sparse search.

    Dense results come from the vector store.
    Sparse results come from BM25 over the document store text.
    Results are merged with Reciprocal Rank Fusion.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore | None = None,
        doc_store: DocumentStore | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        cfg = get_config()
        self._vs = vector_store or build_vector_store()
        self._ds = doc_store or DocumentStore()
        self._embedder = embedder or get_embedder()
        self._dense_k = cfg.rag.dense_top_k
        self._bm25_weight = cfg.rag.bm25_weight
        self._dense_weight = cfg.rag.dense_weight
        self._min_score = cfg.rag.min_score_threshold

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User query string.
            top_k: Number of results to return (default from config).
            source_filter: Optional source_id to restrict results.

        Returns:
            Ranked list of RetrievalResult.
        """
        cfg = get_config().rag
        k = top_k or cfg.rerank_top_k

        # ── Dense retrieval ──────────────────────────────────────────────────
        query_vec = await self._embedder.aembed_one(query)
        where = {"source_id": source_filter} if source_filter else None
        dense_results = self._vs.search(query_vec, top_k=self._dense_k, where=where)

        dense_map: dict[str, VectorSearchResult] = {r.chunk_id: r for r in dense_results}

        # ── Sparse (BM25) retrieval ──────────────────────────────────────────
        all_chunks = self._ds.search_by_text(query, limit=self._dense_k * 2)
        bm25_map: dict[str, dict] = {}

        if all_chunks:
            corpus = [c["text"] for c in all_chunks]
            tokenized = [doc.lower().split() for doc in corpus]
            bm25 = BM25Okapi(tokenized)
            q_tokens = query.lower().split()
            bm25_scores = bm25.get_scores(q_tokens)

            for chunk, score in zip(all_chunks, bm25_scores):
                bm25_map[chunk["chunk_id"]] = {"score": float(score), "chunk": chunk}

        # ── Reciprocal Rank Fusion ───────────────────────────────────────────
        combined: dict[str, dict] = {}

        for rank, result in enumerate(dense_results):
            cid = result.chunk_id
            combined.setdefault(cid, {"dense": 0.0, "sparse": 0.0, "meta": result})
            combined[cid]["dense"] = 1.0 / (rank + 1) * self._dense_weight

        bm25_sorted = sorted(bm25_map.values(), key=lambda x: x["score"], reverse=True)
        for rank, item in enumerate(bm25_sorted):
            cid = item["chunk"]["chunk_id"]
            combined.setdefault(cid, {"dense": 0.0, "sparse": 0.0, "meta": None})
            combined[cid]["sparse"] = 1.0 / (rank + 1) * self._bm25_weight
            if combined[cid]["meta"] is None:
                combined[cid]["meta"] = item["chunk"]

        # ── Build ranked results ─────────────────────────────────────────────
        fused: list[RetrievalResult] = []
        for cid, scores in combined.items():
            total = scores["dense"] + scores["sparse"]
            meta = scores["meta"]
            if isinstance(meta, VectorSearchResult):
                text, metadata = meta.text, meta.metadata
                src = metadata.get("source_path", "")
                section = metadata.get("section", "")
            elif isinstance(meta, dict):
                text = meta.get("text", "")
                metadata = {}
                src = meta.get("source_path", "")
                section = meta.get("section", "")
            else:
                continue

            if total < self._min_score:
                continue

            fused.append(RetrievalResult(
                chunk_id=cid,
                text=text,
                score=total,
                dense_score=scores["dense"],
                sparse_score=scores["sparse"],
                metadata=metadata,
                source_path=src,
                section=section,
            ))

        fused.sort(key=lambda r: r.score, reverse=True)
        log.info("retrieval_done", query_len=len(query), total_candidates=len(fused), top_k=k)
        return fused[:k]
