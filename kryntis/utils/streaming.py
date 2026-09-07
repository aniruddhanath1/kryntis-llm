"""
Streaming utilities.

Provides generator-based helpers for processing large data without
loading entire payloads into RAM.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

DEFAULT_CHUNK_BYTES = 8192  # 8 KB


def stream_file_bytes(path: Path, chunk_size: int = DEFAULT_CHUNK_BYTES) -> Iterator[bytes]:
    """
    Yield `chunk_size` byte chunks from a file without loading it fully.

    Args:
        path: File to read.
        chunk_size: Bytes per chunk.

    Yields:
        Raw byte chunks.
    """
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


async def astream_file_bytes(
    path: Path, chunk_size: int = DEFAULT_CHUNK_BYTES
) -> AsyncIterator[bytes]:
    """Async variant of stream_file_bytes."""
    loop = asyncio.get_event_loop()
    with open(path, "rb") as f:
        while True:
            chunk = await loop.run_in_executor(None, f.read, chunk_size)
            if not chunk:
                break
            yield chunk


def batched(iterable: Iterator[T], n: int) -> Iterator[list[T]]:
    """
    Yield successive n-sized batches from an iterator.

    Args:
        iterable: Source iterator.
        n: Batch size.

    Yields:
        Lists of up to n items.
    """
    batch: list[T] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


async def async_batched(
    iterable: AsyncIterator[T], n: int
) -> AsyncIterator[list[T]]:
    """Async variant of batched."""
    batch: list[T] = []
    async for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


def token_chunked_text(
    text: str,
    chunk_size: int,
    overlap: int,
    count_fn: "Callable[[str], int] | None" = None,
) -> Iterator[str]:
    """
    Split text into overlapping chunks based on rough token counts.

    Uses character-level approximation if no count_fn provided
    (1 token ≈ 4 characters for English).

    Args:
        text: Input text to chunk.
        chunk_size: Target chunk size in tokens.
        overlap: Overlap between consecutive chunks in tokens.
        count_fn: Optional function mapping text → token count.

    Yields:
        Text chunks.
    """
    if count_fn is None:
        # Approximate: 4 chars per token
        chars_per_chunk = chunk_size * 4
        chars_overlap = overlap * 4
        start = 0
        while start < len(text):
            end = start + chars_per_chunk
            yield text[start:end]
            start += chars_per_chunk - chars_overlap
    else:
        # Word-level splitting with token count
        words = text.split()
        start_idx = 0
        current: list[str] = []
        current_tokens = 0

        for word in words:
            wt = count_fn(word + " ")
            if current_tokens + wt > chunk_size and current:
                yield " ".join(current)
                # Roll back overlap
                overlap_words: list[str] = []
                overlap_tokens = 0
                for w in reversed(current):
                    wt2 = count_fn(w + " ")
                    if overlap_tokens + wt2 > overlap:
                        break
                    overlap_words.insert(0, w)
                    overlap_tokens += wt2
                current = overlap_words
                current_tokens = overlap_tokens
            current.append(word)
            current_tokens += count_fn(word + " ")

        if current:
            yield " ".join(current)
