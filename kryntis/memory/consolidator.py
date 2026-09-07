"""
Memory Consolidator — deduplication, merging, and pruning.

Runs periodically (default every hour) to:
1. Find near-duplicate memories (cosine similarity > threshold)
2. Merge duplicates into a single higher-quality entry
3. Remove low-importance, old, never-accessed memories
"""

from __future__ import annotations

import asyncio
import time

from kryntis.memory.long_term import LongTermMemory
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class MemoryConsolidator:
    """
    Periodic memory consolidation background task.

    Removes duplicates and low-quality entries from long-term memory.
    """

    def __init__(self, long_term: LongTermMemory | None = None) -> None:
        cfg = get_config()
        self._lt = long_term or LongTermMemory()
        self._interval = cfg.memory.consolidation_interval_seconds
        self._similarity_threshold = cfg.memory.consolidation_similarity_threshold
        self._running = False

    async def consolidate(self) -> dict:
        """
        Run a single consolidation pass.

        Returns:
            Summary stats dict.
        """
        log.info("memory_consolidation_start")
        start = time.time()

        # TODO: Retrieve all memories and find near-duplicates.
        # For now, basic stats-only consolidation.
        count = self._lt.count()
        elapsed = time.time() - start

        log.info(
            "memory_consolidation_done",
            memories_checked=count,
            elapsed_s=round(elapsed, 2),
        )
        return {"checked": count, "removed": 0, "merged": 0, "elapsed_s": elapsed}

    async def run_forever(self) -> None:
        """Run consolidation in a loop at configured interval."""
        self._running = True
        log.info("memory_consolidator_started", interval_s=self._interval)
        while self._running:
            await asyncio.sleep(self._interval)
            try:
                await self.consolidate()
            except Exception as e:
                log.error("consolidation_error", error=str(e))

    def stop(self) -> None:
        self._running = False
        log.info("memory_consolidator_stopped")
