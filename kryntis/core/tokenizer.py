"""
Byte-Pair Encoding (BPE) Tokenizer for Code.

Code-aware tokenizer built with tokenizers library.
Supports special control tokens and preserves indentation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

CODE_SPECIAL_TOKENS = [
    "<pad>",
    "<unk>",
    "<s>",
    "</s>",
    "<sep>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
    "<|code|>",
    "<|docstring|>",
    "<|comment|>",
    "<|lang:python|>",
    "<|lang:java|>",
    "<|lang:csharp|>",
    "<|lang:javascript|>",
    "<|lang:go|>",
    "<|lang:apex|>",
    "<|lang:abap|>",
]


class CodeBPETokenizer:
    """
    Code-aware BPE Tokenizer for Kryntis Coder models.
    """

    def __init__(self, vocab_size: int = 32000) -> None:
        self.vocab_size = vocab_size
        self._tokenizer = None

    def load(self, model_dir: str | Path = "data/tokenizer") -> None:
        """Load trained tokenizer from disk."""
        path = Path(model_dir) / "tokenizer.json"
        if not path.exists():
            raise FileNotFoundError(f"Tokenizer file not found at {path}")

        from tokenizers import Tokenizer
        self._tokenizer = Tokenizer.from_file(str(path))
        log.info("code_bpe_tokenizer_loaded", vocab_size=self._tokenizer.get_vocab_size())

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer is not loaded or trained yet.")
        encoding = self._tokenizer.encode(text, add_special_tokens=add_special_tokens)
        return encoding.ids

    def decode(self, ids: Sequence[int], skip_special_tokens: bool = True) -> str:
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer is not loaded or trained yet.")
        return self._tokenizer.decode(list(ids), skip_special_tokens=skip_special_tokens)

    @property
    def pad_id(self) -> int:
        return self.encode("<pad>", add_special_tokens=False)[0]

    @property
    def bos_id(self) -> int:
        return self.encode("<s>", add_special_tokens=False)[0]

    @property
    def eos_id(self) -> int:
        return self.encode("</s>", add_special_tokens=False)[0]
