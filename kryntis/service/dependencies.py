"""
Service dependency injection — singleton instances for the lifetime of the app.
"""

from __future__ import annotations

from functools import lru_cache

from kryntis.ingestion.pipeline import IngestionPipeline
from kryntis.knowledge.document_store import DocumentStore
from kryntis.knowledge.vector_store import build_vector_store
from kryntis.learning.continual_learner import ContinualLearner
from kryntis.memory.consolidator import MemoryConsolidator
from kryntis.memory.long_term import LongTermMemory
from kryntis.orchestrator.agent_loop import AIOrchestrator
from kryntis.rag.embedder import get_embedder
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Module-level singleton references
_orchestrator: AIOrchestrator | None = None
_ingestion: IngestionPipeline | None = None
_doc_store: DocumentStore | None = None
_learner: ContinualLearner | None = None
_consolidator: MemoryConsolidator | None = None


async def init_services() -> None:
    """Initialise all singletons at app startup."""
    global _orchestrator, _ingestion, _doc_store, _learner, _consolidator

    log.info("init_services_start")

    # Pre-warm embedder (loads model into RAM once)
    embedder = get_embedder()
    embedder._load()

    vs = build_vector_store()
    _doc_store = DocumentStore()
    _ingestion = IngestionPipeline(vector_store=vs, doc_store=_doc_store)

    lt = LongTermMemory(vector_store=vs)
    _learner = ContinualLearner(long_term=lt)
    _consolidator = MemoryConsolidator(long_term=lt)

    _orchestrator = AIOrchestrator()

    import asyncio
    asyncio.create_task(_consolidator.run_forever())

    log.info("init_services_done")


async def shutdown_services() -> None:
    global _consolidator
    if _consolidator:
        _consolidator.stop()


def get_orchestrator() -> AIOrchestrator:
    assert _orchestrator, "Services not initialised"
    return _orchestrator


def get_ingestion_pipeline() -> IngestionPipeline:
    assert _ingestion, "Services not initialised"
    return _ingestion


def get_doc_store() -> DocumentStore:
    assert _doc_store, "Services not initialised"
    return _doc_store


def get_learner() -> ContinualLearner:
    assert _learner, "Services not initialised"
    return _learner
