"""DOCX chunker — heading-hierarchy-aware extraction via python-docx."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class DOCXChunker(BaseChunker):
    """
    Chunk DOCX files respecting heading hierarchy.

    Groups paragraphs under their nearest heading, creating chunks
    that preserve semantic document structure.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        try:
            from docx import Document
        except ImportError as e:
            raise ImportError("Install python-docx: pip install python-docx") from e

        log.info("docx_chunking_start", path=str(path))
        doc = Document(str(path))

        current_section = ""
        buffer: list[str] = []
        global_index = 0

        def _flush(section: str) -> Iterator[Chunk]:
            nonlocal global_index
            if not buffer:
                return
            text = "\n".join(buffer)
            for seg in self._split_text(text):
                if not seg.strip():
                    continue
                yield Chunk(
                    text=seg,
                    chunk_id=self._make_chunk_id(source_id, global_index),
                    source_id=source_id,
                    source_path=str(path),
                    chunk_index=global_index,
                    total_chunks=0,
                    section=section,
                    chunk_type="text",
                )
                global_index += 1
            buffer.clear()

        for para in doc.paragraphs:
            style = para.style.name if para.style else ""
            text = para.text.strip()
            if not text:
                continue
            if style.startswith("Heading"):
                yield from _flush(current_section)
                current_section = text
            else:
                buffer.append(text)

        yield from _flush(current_section)

        # Also extract tables
        for table in doc.tables:
            rows: list[str] = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                table_text = "\n".join(rows)
                yield Chunk(
                    text=table_text,
                    chunk_id=self._make_chunk_id(source_id, global_index),
                    source_id=source_id,
                    source_path=str(path),
                    chunk_index=global_index,
                    total_chunks=0,
                    section=current_section,
                    chunk_type="table",
                )
                global_index += 1

        log.info("docx_chunking_done", path=str(path), chunks=global_index)
