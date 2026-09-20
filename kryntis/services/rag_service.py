"""RAG Service business logic."""

import asyncio
from typing import List, Dict, Any
from kryntis.rag.retriever import HybridRetriever
from kryntis.rag.context_builder import ContextBuilder, GroundedContextBuilder

class RAGService:
    """Combines hybrid retrieval and context construction."""
    def __init__(self, retriever: HybridRetriever | None = None) -> None:
        self.retriever = retriever or HybridRetriever()
        self.context_builder = ContextBuilder()

    async def abuild_grounded_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        chunks = await self.retriever.retrieve(query, top_k=top_k)
        context_str, citations = self.context_builder.build(chunks)
        return {
            "context": context_str,
            "citations": citations,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "score": c.score,
                    "source_path": c.source_path,
                    "section": c.section,
                }
                for c in chunks
            ]
        }

    def build_grounded_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self.abuild_grounded_context(query, top_k=top_k))
        return asyncio.run(self.abuild_grounded_context(query, top_k=top_k))
