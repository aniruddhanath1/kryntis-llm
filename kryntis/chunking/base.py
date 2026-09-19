"""
Base Chunker — defines the Chunk dataclass and BaseChunker abstract class.

Every chunker in kryntis/chunking/ inherits from BaseChunker.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class Chunk:
    """A chunk of text extracted from a document with full provenance."""

    text: str
    chunk_id: str                   # Deterministic hash of source_id + index
    source_id: str                  # Stable document identifier (e.g. file hash or UUID)
    source_path: str                # Original file path or URL
    chunk_index: int                # 0-based position in document
    total_chunks: int               # Total chunks for this document (-1 if streaming)

    # Optional metadata
    page: int | None = None         # PDF/PPTX page or slide number (1-based)
    section: str = ""               # Header/section title if available
    language: str = ""              # Detected programming/human language
    mime_type: str = ""
    token_count: int = 0            # Approximate token count (len(text) // 4)
    metadata: dict = field(default_factory=dict)
    chunk_type: str = "text"        # "text" | "code" | "table" | "image" | "audio" | "video"

    def __post_init__(self) -> None:
        if not self.token_count:
            self.token_count = max(1, len(self.text) // 4)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "text": self.text,
            "page": self.page,
            "section": self.section,
            "language": self.language,
            "mime_type": self.mime_type,
            "token_count": self.token_count,
            "chunk_type": self.chunk_type,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class BaseChunker(ABC):
    """
    Abstract base class for all document chunkers.

    Subclasses must implement:
      - chunk_file(path, source_id) -> Iterator[Chunk]
      - supported_extensions -> list[str]

    Subclasses should respect self.chunk_size and self.chunk_overlap.
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
        Extract chunks from a file on disk.

        Args:
            path: Absolute path to the file.
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

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _make_chunk_id(source_id: str, index: int) -> str:
        import hashlib
        try:
            import xxhash
            raw = f"{source_id}:{index}".encode("utf-8")
            return xxhash.xxh64_hexdigest(raw)
        except Exception:
            raw = f"{source_id}:{index}".encode("utf-8")
            return hashlib.sha256(raw).hexdigest()[:16]

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
