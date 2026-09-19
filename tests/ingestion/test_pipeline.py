"""Tests for direct-text chunked ingestion."""

import asyncio
import unittest
from unittest.mock import AsyncMock

from kryntis.ingestion.pipeline import IngestionPipeline


class TestPipeline(unittest.IsolatedAsyncioTestCase):

    async def test_ingest_text_routes_through_file_ingestion(self) -> None:
        """Text input becomes a temporary text source for shared chunking."""
        pipeline = object.__new__(IngestionPipeline)
        pipeline.ingest_files = AsyncMock(return_value="job")

        result = await pipeline.ingest_text("x" * 300, "manual-note")

        self.assertEqual(result, "job")
        self.assertEqual(pipeline.ingest_files.await_args.args[0][0].suffix, ".txt")

    async def test_ingest_text_rejects_blank_input(self) -> None:
        """Blank text cannot create an ingestible source."""
        pipeline = object.__new__(IngestionPipeline)
        with self.assertRaises(ValueError):
            await pipeline.ingest_text("  ")


if __name__ == "__main__":
    unittest.main()
