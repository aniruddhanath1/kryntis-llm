"""Native TS / Byte Engine operations."""

from typing import List

class ByteDirectEngine:
    """Fast native byte tokenizer-free conversion."""
    @staticmethod
    def encode(text: str) -> List[int]:
        return list(text.encode("utf-8"))

    @staticmethod
    def decode(bytes_list: List[int]) -> str:
        return bytes(bytes_list).decode("utf-8", errors="replace")
