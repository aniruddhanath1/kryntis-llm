"""Query Executor for semantic RAG queries."""

import asyncio
from typing import Dict, Any, List
from kryntis.rag.retriever import HybridRetriever
from kryntis.knowledge.vector_store import BaseVectorStore, build_vector_store
from kryntis.knowledge.document_store import DocumentStore, SQLiteDocumentStore

class QueryExecutor:
    """Dispatches semantic hybrid search against stored corpus."""
    def __init__(
        self,
        vector_store: BaseVectorStore | None = None,
        doc_store: DocumentStore | None = None,
    ) -> None:
        self.doc_store = doc_store or DocumentStore()
        self.vector_store = vector_store or build_vector_store()
        self.retriever = HybridRetriever(doc_store=self.doc_store, vector_store=self.vector_store)

    async def asearch(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        chunks = await self.retriever.retrieve(query_text, top_k=top_k)
        return [
            {
                "chunk_id": c.chunk_id,
                "content": c.text,
                "score": c.score,
                "source_path": c.source_path,
                "section": c.section,
                "metadata": c.metadata,
            }
            for c in chunks
        ]

    def search(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self.asearch(query_text, top_k=top_k))
        return asyncio.run(self.asearch(query_text, top_k=top_k))
