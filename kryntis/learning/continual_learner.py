"""
Continual Learning — queues approved knowledge for incremental ingestion.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from kryntis.ingestion.pipeline import IngestionPipeline
from kryntis.memory.long_term import LongTermMemory
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class LearningCandidate:
    """A piece of knowledge waiting to be learned."""
    candidate_id: str
    content: str
    source: str
    confidence: float
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    approved: bool = False


class ContinualLearner:
    """
    Manages the continual learning queue.

    New facts from internet research, conversation, or documents
    are queued as candidates. Approved candidates are persisted
    into long-term memory and the vector store.

    This ensures Kryntis AI only learns from validated information.
    """

    def __init__(
        self,
        long_term: LongTermMemory | None = None,
        pipeline: IngestionPipeline | None = None,
    ) -> None:
        cfg = get_config()
        self._lt = long_term or LongTermMemory()
        self._pipeline = pipeline or IngestionPipeline()
        self._queue: list[LearningCandidate] = []
        self._min_confidence = cfg.learning.min_confidence
        self._auto_approve = cfg.learning.auto_approve_above_confidence

    def enqueue(
        self,
        content: str,
        source: str,
        confidence: float,
        auto_approve: bool = False,
    ) -> LearningCandidate:
        """Add content to the learning queue."""
        candidate = LearningCandidate(
            candidate_id=str(uuid.uuid4()),
            content=content,
            source=source,
            confidence=confidence,
        )
        if auto_approve or confidence >= self._auto_approve:
            candidate.approved = True
        self._queue.append(candidate)
        log.debug(
            "learning_enqueued",
            candidate_id=candidate.candidate_id,
            approved=candidate.approved,
            confidence=confidence,
        )
        return candidate

    async def process_approved(self) -> int:
        """Persist all approved candidates to long-term memory."""
        approved = [c for c in self._queue if c.approved and c.confidence >= self._min_confidence]
        count = 0
        for candidate in approved:
            try:
                await self._lt.store(
                    content=candidate.content,
                    session_id="learning",
                    importance=candidate.confidence,
                    tags=["learned", candidate.source],
                )
                self._queue.remove(candidate)
                count += 1
            except Exception as e:
                log.error("learning_store_error", error=str(e))
        log.info("learning_processed", approved=count, remaining=len(self._queue))
        return count

    def approve(self, candidate_id: str) -> bool:
        for c in self._queue:
            if c.candidate_id == candidate_id:
                c.approved = True
                return True
        return False

    def list_pending(self) -> list[LearningCandidate]:
        return [c for c in self._queue if not c.approved]

    def list_approved(self) -> list[LearningCandidate]:
        return [c for c in self._queue if c.approved]
