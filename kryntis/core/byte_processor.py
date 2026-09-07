"""
Byte / ASCII Direct Processing Engine — Tokenizer-Free Byte Level Encoding for Kryntis AI.

Direct 256-Byte / ASCII / UTF-8 mapping (Byte-level language modeling):
No vocabulary tables, no word dictionaries, no BPE tokenization.
Every character/byte is mapped directly to its exact 0-255 byte byte value or 8-bit binary representation.
"""

from __future__ import annotations

import torch


class ByteDirectProcessor:
    """
    Direct Byte-level / ASCII language processor.

    Maps text directly into bytes [0..255] and binary bit streams.
    Vocab size is strictly 256 (or 260 including special control bytes).
    """

    PAD_BYTE = 0
    BOS_BYTE = 256
    EOS_BYTE = 257
    UNK_BYTE = 258
    MASK_BYTE = 259

    VOCAB_SIZE = 260

    def __init__(self) -> None:
        self.vocab_size = self.VOCAB_SIZE

    def encode(self, text: str) -> list[int]:
        """Convert raw text directly to its UTF-8 / ASCII byte values [0..255]."""
        if not text:
            return []
        byte_vals = list(text.encode("utf-8", errors="replace"))
        return byte_vals

    def decode(self, bytes_list: list[int]) -> str:
        """Convert byte values [0..255] back directly to human readable text."""
        valid_bytes = bytearray([b for b in bytes_list if 0 <= b < 256])
        return valid_bytes.decode("utf-8", errors="replace")

    def text_to_binary_matrix(self, text: str) -> torch.Tensor:
        """
        Convert text directly into its 8-bit binary representation.
        Returns Tensor of shape (len(text), 8) containing bits (0 or 1).
        """
        raw_bytes = self.encode(text)
        bits_list = []
        for b in raw_bytes:
            bits = [(b >> i) & 1 for i in range(7, -1, -1)]
            bits_list.append(bits)
        return torch.tensor(bits_list, dtype=torch.float32)

    def binary_matrix_to_text(self, bits_tensor: torch.Tensor) -> str:
        """Convert 8-bit binary tensor back into human readable text."""
        bits = bits_tensor.int().tolist()
        byte_vals = []
        for b_arr in bits:
            val = 0
            for bit in b_arr:
                val = (val << 1) | (1 if bit > 0 else 0)
            byte_vals.append(val)
        return self.decode(byte_vals)
