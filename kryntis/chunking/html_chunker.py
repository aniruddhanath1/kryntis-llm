"""HTML chunker — section and article extraction via BeautifulSoup."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_BLOCK_TAGS = {"p", "li", "td", "th", "pre", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}


class HTMLChunker(BaseChunker):
    """
    Chunk HTML files by semantic structure.

    Extracts text from block-level elements respecting heading
    hierarchy for section context.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".html", ".htm", ".xhtml"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        from bs4 import BeautifulSoup

        log.info("html_chunking_start", path=str(path))
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            soup = BeautifulSoup(f, "lxml")

        # Remove boilerplate
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()

        current_section = ""
        global_index = 0
        buffer: list[str] = []

        def _flush() -> Iterator[Chunk]:
            nonlocal global_index, buffer
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
                    section=current_section,
                    chunk_type="text",
                )
                global_index += 1
            buffer.clear()

        for element in soup.find_all(_BLOCK_TAGS):
            text = element.get_text(" ", strip=True)
            if not text:
                continue
            tag = element.name
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                yield from _flush()
                current_section = text
            else:
                buffer.append(text)

        yield from _flush()
        log.info("html_chunking_done", path=str(path), chunks=global_index)
