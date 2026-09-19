"""Spreadsheet chunker — XLSX/XLS/CSV with per-sheet and row-batch chunking."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kryntis.chunking.base import BaseChunker, Chunk
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_ROWS_PER_CHUNK = 50  # Rows per chunk for large sheets


class SpreadsheetChunker(BaseChunker):
    """
    Chunk Excel (XLSX/XLS) and CSV files.

    Strategy:
    - Each sheet becomes a logical section.
    - Rows are grouped into batches of _ROWS_PER_CHUNK.
    - Headers are repeated at the start of each chunk for context.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls", ".csv"]

    def chunk_file(self, path: Path, source_id: str) -> Iterator[Chunk]:
        import pandas as pd

        log.info("spreadsheet_chunking_start", path=str(path))
        ext = path.suffix.lower()
        global_index = 0

        if ext == ".csv":
            sheets = {"Sheet1": pd.read_csv(str(path), dtype=str, na_filter=False)}
        else:
            xl = pd.ExcelFile(str(path), engine="openpyxl")
            sheets = {
                name: xl.parse(name, dtype=str, na_values="").fillna("")
                for name in xl.sheet_names
            }

        for sheet_name, df in sheets.items():
            if df.empty:
                continue
            headers = list(df.columns)
            header_line = " | ".join(str(h) for h in headers)

            # Process rows in batches
            for batch_start in range(0, len(df), _ROWS_PER_CHUNK):
                batch = df.iloc[batch_start: batch_start + _ROWS_PER_CHUNK]
                row_lines: list[str] = [f"[Headers]: {header_line}"]
                for _, row in batch.iterrows():
                    row_text = " | ".join(str(v) for v in row.values)
                    row_lines.append(row_text)

                chunk_text = "\n".join(row_lines)
                yield Chunk(
                    text=chunk_text,
                    chunk_id=self._make_chunk_id(source_id, global_index),
                    source_id=source_id,
                    source_path=str(path),
                    chunk_index=global_index,
                    total_chunks=0,
                    section=sheet_name,
                    chunk_type="table",
                    metadata={
                        "sheet": sheet_name,
                        "row_start": batch_start,
                        "row_end": batch_start + len(batch),
                    },
                )
                global_index += 1

        log.info("spreadsheet_chunking_done", path=str(path), chunks=global_index)
