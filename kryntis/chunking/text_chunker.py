"""Plain text chunker — paragraph and semantic boundary splitting."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class TextChunker(BaseChunker):
    """
    Chunk plain text and Markdown files.

    Splits on paragraph boundaries (double newlines) first,
    then applies token-limit splitting within large paragraphs.
    Detects Markdown headings for section tracking.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".txt", ".md", ".rst", ".log"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        log.info("text_chunking_start", path=str(path))
        global_index = 0
        current_section = ""

        # Stream file in manageable blocks
        buffer = ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                buffer += raw_line

                # Process paragraph boundaries
                while "\n\n" in buffer:
                    para, buffer = buffer.split("\n\n", 1)
                    para = para.strip()
                    if not para:
                        continue

                    # Detect markdown headings
                    if para.startswith("#"):
                        current_section = para.lstrip("#").strip()

                    for seg in self._split_text(para):
                        if len(seg) < self.min_chunk_size * 4:
                            continue
                        yield Chunk(
                            text=seg,
                            chunk_id=self._make_chunk_id(source_id, global_index),
                            source_id=source_id,
                            source_path=str(path),
                            chunk_index=global_index,
                            total_chunks=0,
                            section=current_section,
                            chunk_type="text",
                        )
                        global_index += 1

        # Flush remaining buffer
        if buffer.strip():
            for seg in self._split_text(buffer.strip()):
                if len(seg) >= self.min_chunk_size * 4:
                    yield Chunk(
                        text=seg,
                        chunk_id=self._make_chunk_id(source_id, global_index),
                        source_id=source_id,
                        source_path=str(path),
                        chunk_index=global_index,
                        total_chunks=0,
                        section=current_section,
                        chunk_type="text",
                    )
                    global_index += 1

        log.info("text_chunking_done", path=str(path), chunks=global_index)
