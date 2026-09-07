"""Image chunker — extracts alt text, EXIF metadata, and runs OCR when available."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class ImageChunker(BaseChunker):
    """
    Chunk image files.

    Extracts:
    - EXIF metadata (camera, date, GPS)
    - OCR text via pytesseract (if installed)
    - File metadata as a structured chunk

    If pytesseract is not installed, emits a metadata-only chunk.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        from PIL import Image, ExifTags

        log.info("image_chunking_start", path=str(path))
        parts: list[str] = [f"[Image]: {path.name}"]
        metadata: dict = {"filename": path.name}

        try:
            img = Image.open(str(path))
            parts.append(f"Format: {img.format}, Mode: {img.mode}, Size: {img.size}")
            metadata.update({"format": img.format, "mode": img.mode, "size": list(img.size)})

            # EXIF
            exif_data = img._getexif() if hasattr(img, "_getexif") else None
            if exif_data:
                readable = {
                    ExifTags.TAGS.get(k, k): str(v)
                    for k, v in exif_data.items()
                    if k in ExifTags.TAGS and v
                }
                exif_text = ", ".join(f"{k}: {v}" for k, v in list(readable.items())[:10])
                parts.append(f"EXIF: {exif_text}")
                metadata["exif"] = readable
        except Exception as e:
            log.warning("image_metadata_error", path=str(path), error=str(e))

        # OCR
        try:
            import pytesseract
            img_gray = img.convert("L")
            ocr_text = pytesseract.image_to_string(img_gray).strip()
            if ocr_text:
                parts.append(f"[OCR Text]:\n{ocr_text}")
        except ImportError:
            log.debug("pytesseract_not_installed", msg="No OCR for images")
        except Exception as e:
            log.warning("ocr_error", path=str(path), error=str(e))

        chunk_text = "\n".join(parts)
        yield Chunk(
            text=chunk_text,
            chunk_id=self._make_chunk_id(source_id, 0),
            source_id=source_id,
            source_path=str(path),
            chunk_index=0,
            total_chunks=1,
            chunk_type="image_caption",
            metadata=metadata,
        )
        log.info("image_chunking_done", path=str(path))
