"""
Chunking engine base classes and Chunk dataclass.

All chunkers produce a uniform list of Chunk objects that carry
both the text payload and rich metadata for RAG retrieval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Chunk:
    """
    A discrete unit of content extracted from a document.

    Attributes:
        text: The raw text content of the chunk.
        chunk_id: Unique identifier (source_hash + position).
        source_id: Identifier of the parent document.
        source_path: File path or URL of origin.
        chunk_index: Position within the document (0-based).
        total_chunks: Total chunks in this document.
        page: Page number (PDFs, DOCX) or slide (PPTX).
        section: Section/heading hierarchy (e.g. "Chapter 1 > Intro").
        chunk_type: "text" | "table" | "code" | "image_caption" | "header".
        language: Detected language code (e.g. "en").
        token_count: Approximate token count.
        parent_id: ID of parent chunk (for hierarchical chunking).
        metadata: Arbitrary extra key-value pairs.
    """

    text: str
    chunk_id: str
    source_id: str
    source_path: str
    chunk_index: int = 0
    total_chunks: int = 1
    page: int | None = None
    section: str = ""
    chunk_type: str = "text"
    language: str = "en"
    token_count: int = 0
    parent_id: str | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.token_count:
            # Approximate: 1 token ≈ 4 chars
            self.token_count = max(1, len(self.text) // 4)

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for storage)."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "page": self.page,
            "section": self.section,
            "chunk_type": self.chunk_type,
            "language": self.language,
            "token_count": self.token_count,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
        }


class BaseChunker(ABC):
    """
    Abstract chunker interface.

    Every format-specific chunker must implement `chunk_file()`,
    which streams Chunk objects without loading the full file into RAM.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 50,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    @abstractmethod
    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        """
        Stream Chunk objects from a file.

        Args:
            path: Path to the file on disk.
            source_id: Stable identifier for the source document.

        Yields:
            Chunk objects in document order.
        """
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this chunker handles (e.g. ['.pdf'])."""
        ...

    # ── Utilities ──────────────────────────────────────────────────────────

    @staticmethod
    def _make_chunk_id(source_id: str, index: int) -> str:
        import xxhash
        raw = f"{source_id}:{index}"
        return xxhash.xxh64_hexdigest(raw)

    def _split_text(self, text: str) -> list[str]:
        """
        Split a block of text into overlapping token-bounded chunks.

        Uses character-level approximation (4 chars ≈ 1 token).
        """
        char_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + char_size, len(text))
            segment = text[start:end].strip()
            if len(segment) >= self.min_chunk_size * 4:
                chunks.append(segment)
            start += char_size - char_overlap
        return chunks

    def _make_chunks(
        self,
        segments: list[str],
        source_id: str,
        source_path: str,
        page: int | None = None,
        section: str = "",
        chunk_type: str = "text",
        index_offset: int = 0,
    ) -> Iterator[Chunk]:
        """Helper: convert text segments to Chunk objects."""
        total = len(segments)
        for i, text in enumerate(segments):
            if not text.strip():
                continue
            idx = index_offset + i
            yield Chunk(
                text=text,
                chunk_id=self._make_chunk_id(source_id, idx),
                source_id=source_id,
                source_path=source_path,
                chunk_index=idx,
                total_chunks=total,
                page=page,
                section=section,
                chunk_type=chunk_type,
            )
