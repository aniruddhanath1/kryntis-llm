"""
Code chunker — function/class-block-aware splitting.

Splits source code files at semantic boundaries (function/class
definitions) rather than raw character counts.

Supports: Python, JS/TS, Java, C/C++, Go, Rust, and falls back
to line-based chunking for unknown languages.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Regex patterns to detect top-level function/class boundaries
_BOUNDARIES: dict[str, re.Pattern] = {
    ".py":   re.compile(r"^(def |class |async def )", re.M),
    ".js":   re.compile(r"^(function |const |class |export )", re.M),
    ".ts":   re.compile(r"^(function |const |class |interface |export )", re.M),
    ".java": re.compile(r"^(\s*(public|private|protected|class|interface|enum)\b)", re.M),
    ".go":   re.compile(r"^(func |type )", re.M),
    ".rs":   re.compile(r"^(fn |impl |struct |enum |pub fn )", re.M),
    ".c":    re.compile(r"^[a-zA-Z_][\w\s\*]+\(", re.M),
    ".cpp":  re.compile(r"^[a-zA-Z_][\w\s\*]+\(", re.M),
}

_CODE_EXTENSIONS = list(_BOUNDARIES.keys()) + [
    ".jsx", ".tsx", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh", ".bash"
]


class CodeChunker(BaseChunker):
    """
    Chunk source code by semantic block boundaries.

    Detects function/class definitions and groups lines between
    them into chunks. Falls back to line-based batching for
    unknown languages.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return _CODE_EXTENSIONS

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        log.info("code_chunking_start", path=str(path))
        ext = path.suffix.lower()

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()

        pattern = _BOUNDARIES.get(ext)
        global_index = 0

        if pattern:
            # Split at semantic boundaries
            boundaries = [m.start() for m in pattern.finditer(source)]
            if not boundaries:
                boundaries = [0]
            if boundaries[0] != 0:
                boundaries = [0] + boundaries
            boundaries.append(len(source))

            for i in range(len(boundaries) - 1):
                block = source[boundaries[i]: boundaries[i + 1]].strip()
                if not block or len(block) < self.min_chunk_size * 4:
                    continue
                # Further split very large blocks
                for seg in self._split_text(block):
                    if not seg.strip():
                        continue
                    yield Chunk(
                        text=seg,
                        chunk_id=self._make_chunk_id(source_id, global_index),
                        source_id=source_id,
                        source_path=str(path),
                        chunk_index=global_index,
                        total_chunks=0,
                        section=ext.lstrip(".").upper(),
                        chunk_type="code",
                        metadata={"language": ext.lstrip(".")},
                    )
                    global_index += 1
        else:
            # Line-batch fallback
            lines = source.splitlines()
            batch_size = self.chunk_size  # lines per chunk
            for i in range(0, len(lines), batch_size):
                block = "\n".join(lines[i: i + batch_size]).strip()
                if not block:
                    continue
                yield Chunk(
                    text=block,
                    chunk_id=self._make_chunk_id(source_id, global_index),
                    source_id=source_id,
                    source_path=str(path),
                    chunk_index=global_index,
                    total_chunks=0,
                    chunk_type="code",
                    metadata={"language": ext.lstrip(".")},
                )
                global_index += 1

        log.info("code_chunking_done", path=str(path), chunks=global_index)
