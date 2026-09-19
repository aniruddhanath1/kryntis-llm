"""
Streaming Dataset Loader — Memory-efficient tokenized batch generator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import torch
from typing import Iterator, Any

import torch
from torch.utils.data import IterableDataset, DataLoader


class StreamingCodeDataset(IterableDataset):
    """
    Streaming PyTorch IterableDataset for pretraining.
    Tokenizes text on-the-fly and yields fixed-length token windows.
    """

    def __init__(
        self,
        jsonl_path: str | Path,
        tokenizer: Any,
        max_seq_len: int = 256,
    ) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len

    def __iter__(self) -> Iterator[dict[str, torch.Tensor]]:
        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"Training corpus not found at {self.jsonl_path}")

        token_buffer: list[int] = []

        with open(self.jsonl_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    text = data.get("text", "")
                    if not text:
                        continue

                    # Tokenize and append to buffer
                    tokens = self.tokenizer.encode(text, add_special_tokens=True)
                    token_buffer.extend(tokens)

                    # Yield full sequence chunks
                    while len(token_buffer) >= self.max_seq_len + 1:
                        chunk = token_buffer[: self.max_seq_len + 1]
                        token_buffer = token_buffer[self.max_seq_len :]

                        x = torch.tensor(chunk[:-1], dtype=torch.long)
                        y = torch.tensor(chunk[1:], dtype=torch.long)
                        yield {"input_ids": x, "labels": y}
                except Exception:
                    continue


def create_dataloader(
    jsonl_path: str | Path,
    tokenizer: Any,
    batch_size: int = 2,
    max_seq_len: int = 256,
) -> DataLoader:
    dataset = StreamingCodeDataset(jsonl_path, tokenizer, max_seq_len)
    return DataLoader(dataset, batch_size=batch_size)
