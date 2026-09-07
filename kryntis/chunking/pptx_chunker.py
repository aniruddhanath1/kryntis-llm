"""PPTX chunker — slide-by-slide extraction with notes via python-pptx."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class PPTXChunker(BaseChunker):
    """
    Chunk PPTX files slide by slide.

    Each slide produces a chunk containing title, body text, and
    speaker notes merged together.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pptx", ".ppt"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        try:
            from pptx import Presentation
            from pptx.util import Pt
        except ImportError as e:
            raise ImportError("Install python-pptx: pip install python-pptx") from e

        log.info("pptx_chunking_start", path=str(path))
        prs = Presentation(str(path))

        for slide_num, slide in enumerate(prs.slides, start=1):
            parts: list[str] = []
            title = ""

            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if not text:
                        continue
                    # Detect title by shape name or first large-font paragraph
                    if shape.name.lower() in ("title", "subtitle") and not title:
                        title = text
                    else:
                        parts.append(text)

            # Include speaker notes
            if slide.has_notes_slide:
                notes_tf = slide.notes_slide.notes_text_frame
                notes_text = notes_tf.text.strip()
                if notes_text:
                    parts.append(f"[Notes]: {notes_text}")

            full_text = (f"[Slide {slide_num}] {title}\n" if title else f"[Slide {slide_num}]\n")
            full_text += "\n".join(parts)

            for seg in self._split_text(full_text):
                if not seg.strip():
                    continue
                yield Chunk(
                    text=seg,
                    chunk_id=self._make_chunk_id(source_id, slide_num - 1),
                    source_id=source_id,
                    source_path=str(path),
                    chunk_index=slide_num - 1,
                    total_chunks=len(prs.slides),
                    page=slide_num,
                    section=title,
                    chunk_type="text",
                    metadata={"slide": slide_num, "slide_title": title},
                )

        log.info("pptx_chunking_done", path=str(path), slides=len(prs.slides))
