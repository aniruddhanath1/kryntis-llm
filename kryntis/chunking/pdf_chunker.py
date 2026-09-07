"""PDF chunker — page-aware, heading-aware extraction via PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class PDFChunker(BaseChunker):
    """
    Chunk PDF files by page and semantic paragraph boundaries.

    Uses PyMuPDF (fitz) for fast streaming page extraction.
    Large PDFs are processed page-by-page without full RAM load.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ImportError("Install PyMuPDF: pip install PyMuPDF") from e

        log.info("pdf_chunking_start", path=str(path))
        global_index = 0
        doc = fitz.open(str(path))

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,block_type)

            current_section = ""
            page_texts: list[str] = []

            for block in blocks:
                text = block[4].strip()
                if not text:
                    continue
                # Heuristic: short lines in large font → heading
                if len(text) < 120 and text.endswith(("\n", "")):
                    current_section = text.replace("\n", " ").strip()
                page_texts.append(text)

            full_page_text = "\n".join(page_texts)
            segments = self._split_text(full_page_text)

            for seg in segments:
                if not seg.strip():
                    continue
                yield Chunk(
                    text=seg,
                    chunk_id=self._make_chunk_id(source_id, global_index),
                    source_id=source_id,
                    source_path=str(path),
                    chunk_index=global_index,
                    total_chunks=0,  # Updated by pipeline after counting
                    page=page_num + 1,
                    section=current_section,
                    chunk_type="text",
                    metadata={"pdf_page": page_num + 1, "pdf_total_pages": len(doc)},
                )
                global_index += 1

        doc.close()
        log.info("pdf_chunking_done", path=str(path), chunks=global_index)
