"""
Chunk Router — maps file extensions to the correct chunker.

This is the single entry point for all chunking operations.
The router is also where you configure chunker parameters globally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.chunking.code_chunker import CodeChunker
from kryntis.chunking.docx_chunker import DOCXChunker
from kryntis.chunking.html_chunker import HTMLChunker
from kryntis.chunking.image_chunker import ImageChunker
from kryntis.chunking.json_chunker import JSONChunker
from kryntis.chunking.pdf_chunker import PDFChunker
from kryntis.chunking.pptx_chunker import PPTXChunker
from kryntis.chunking.spreadsheet_chunker import SpreadsheetChunker
from kryntis.chunking.text_chunker import TextChunker
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class ChunkRouter:
    """
    Routes files to the appropriate chunker based on extension.

    All chunkers are instantiated once with shared config settings.
    Custom chunkers can be registered at runtime.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        cfg = get_config().chunking
        size = chunk_size or cfg.default_chunk_size
        overlap = chunk_overlap or cfg.default_chunk_overlap
        min_size = cfg.min_chunk_size

        self._chunkers: list[BaseChunker] = [
            PDFChunker(size, overlap, min_size),
            DOCXChunker(size, overlap, min_size),
            PPTXChunker(size, overlap, min_size),
            SpreadsheetChunker(size, overlap, min_size),
            HTMLChunker(size, overlap, min_size),
            JSONChunker(size, overlap, min_size),
            CodeChunker(size, overlap, min_size),
            ImageChunker(size, overlap, min_size),
            TextChunker(size, overlap, min_size),  # Fallback last
        ]

        self._ext_map: dict[str, BaseChunker] = {}
        for chunker in self._chunkers:
            for ext in chunker.supported_extensions:
                self._ext_map[ext.lower()] = chunker

    def register(self, chunker: BaseChunker) -> None:
        """Register a custom chunker (overrides built-ins for its extensions)."""
        for ext in chunker.supported_extensions:
            self._ext_map[ext.lower()] = chunker
        log.info("custom_chunker_registered", extensions=chunker.supported_extensions)

    def get_chunker(self, path: Path) -> BaseChunker | None:
        """Return the chunker for this file, or None if unsupported."""
        ext = path.suffix.lower()
        return self._ext_map.get(ext)

    def can_chunk(self, path: Path) -> bool:
        """Return True if we have a chunker for this file type."""
        return path.suffix.lower() in self._ext_map

    def chunk(self, path: Path, source_id: str) -> Iterator[Chunk]:
        """
        Route a file to the correct chunker and stream Chunks.

        Args:
            path: File path.
            source_id: Stable document identifier.

        Yields:
            Chunk objects.

        Raises:
            ValueError: If file type is not supported.
        """
        chunker = self.get_chunker(path)
        if chunker is None:
            raise ValueError(
                f"No chunker available for '{path.suffix}'. "
                f"Supported: {sorted(self._ext_map.keys())}"
            )
        log.info("chunking_file", path=str(path), chunker=type(chunker).__name__)
        yield from chunker.chunk_file(path, source_id)

    @property
    def supported_extensions(self) -> list[str]:
        return sorted(self._ext_map.keys())
