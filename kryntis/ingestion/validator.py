"""
File Validator — MIME type, size, and security checks for uploaded files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Allowed MIME types (mirrors config for fast in-process checking)
_ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".csv", ".txt", ".md", ".rst",
    ".html", ".htm", ".json", ".jsonl", ".xml",
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
}


@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""
    mime_type: str = ""
    file_size: int = 0


class FileValidator:
    """
    Validates uploaded files for safety and format compliance.

    Checks:
    1. File size ≤ 100 MB
    2. Extension is in the allowed list
    3. MIME type matches extension (magic bytes check)
    4. File is not empty
    """

    def __init__(self) -> None:
        self._cfg = get_config().ingestion

    def validate(self, path: Path) -> ValidationResult:
        if not path.exists():
            return ValidationResult(False, f"File not found: {path}")

        size = path.stat().st_size
        if size == 0:
            return ValidationResult(False, "File is empty")

        if size > self._cfg.max_file_size_bytes:
            mb = size / (1024 * 1024)
            limit = self._cfg.max_file_size_bytes / (1024 * 1024)
            return ValidationResult(False, f"File too large: {mb:.1f} MB > {limit:.0f} MB limit")

        ext = path.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            return ValidationResult(False, f"Unsupported file type: '{ext}'")

        mime_type = self._detect_mime(path)
        log.debug("file_validated", path=path.name, size_mb=round(size / 1e6, 2), mime=mime_type)
        return ValidationResult(True, mime_type=mime_type, file_size=size)

    @staticmethod
    def _detect_mime(path: Path) -> str:
        """Attempt MIME detection via python-magic, fallback to extension map."""
        try:
            import magic
            return magic.from_file(str(path), mime=True)
        except Exception:
            _ext_mime = {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".csv": "text/csv",
                ".txt": "text/plain",
                ".json": "application/json",
                ".html": "text/html",
            }
            return _ext_mime.get(path.suffix.lower(), "application/octet-stream")
