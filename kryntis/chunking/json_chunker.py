"""JSON chunker — path-aware recursive extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class JSONChunker(BaseChunker):
    """
    Chunk JSON files by value-level extraction.

    Walks the JSON tree and emits chunks for string values and
    arrays, tagging each with its JSON path for context.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".json", ".jsonl", ".ndjson"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        log.info("json_chunking_start", path=str(path))
        global_index = 0

        ext = path.suffix.lower()

        if ext in (".jsonl", ".ndjson"):
            # JSON Lines: one object per line
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = self._obj_to_text(obj, path=f"[line {line_num}]")
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
                            section=f"line {line_num}",
                            chunk_type="text",
                        )
                        global_index += 1
        else:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    log.warning("json_parse_error", path=str(path), error=str(e))
                    return

            for chunk_text, json_path in self._walk(data, "root"):
                for seg in self._split_text(chunk_text):
                    if not seg.strip():
                        continue
                    yield Chunk(
                        text=seg,
                        chunk_id=self._make_chunk_id(source_id, global_index),
                        source_id=source_id,
                        source_path=str(path),
                        chunk_index=global_index,
                        total_chunks=0,
                        section=json_path,
                        chunk_type="text",
                        metadata={"json_path": json_path},
                    )
                    global_index += 1

        log.info("json_chunking_done", path=str(path), chunks=global_index)

    def _walk(self, obj: Any, path: str) -> Iterator[tuple[str, str]]:
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            batch: list[str] = []
            for i, item in enumerate(obj):
                if isinstance(item, (str, int, float, bool)):
                    batch.append(str(item))
                else:
                    yield from self._walk(item, f"{path}[{i}]")
                if len(batch) >= 20:
                    yield "\n".join(batch), path
                    batch = []
            if batch:
                yield "\n".join(batch), path
        elif isinstance(obj, str) and len(obj) > 20:
            yield obj, path

    def _obj_to_text(self, obj: Any, path: str = "root") -> str:
        parts: list[str] = []
        for text, _ in self._walk(obj, path):
            parts.append(text)
        return "\n".join(parts)
