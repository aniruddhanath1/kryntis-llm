"""
Word/Lexical Tokenizer — Natural English words & punctuation without BPE subwords.

Splits text on natural word boundaries, preserves punctuation, handles casing,
and includes special control tokens. Uses an explicit Vocabulary with an <unk> token.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Sequence

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

ENGLISH_SPECIAL_TOKENS = [
    "<pad>",
    "<unk>",
    "<s>",
    "</s>",
    "<sep>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
    "<|code|>",
    "<|emotion:joy|>",
    "<|emotion:sadness|>",
    "<|emotion:anger|>",
    "<|emotion:fear|>",
    "<|emotion:empathy|>",
    "<|emotion:neutral|>",
]

# Regex to capture words, numbers, and punctuation as discrete tokens
_TOKEN_REGEX = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class NaturalEnglishTokenizer:
    """
    Word-level Natural Language & Code Tokenizer.

    Processes text as natural English words and punctuation symbols without BPE subword splitting.
    Human-readable vocabulary built directly from raw words.
    """

    def __init__(self, vocab_size: int = 50000) -> None:
        self.vocab_size = vocab_size
        self.word2idx: dict[str, int] = {}
        self.idx2word: dict[int, str] = {}
        self._init_special_tokens()

    def _init_special_tokens(self) -> None:
        for idx, token in enumerate(ENGLISH_SPECIAL_TOKENS):
            self.word2idx[token] = idx
            self.idx2word[idx] = token

    def build_vocab(self, corpus_path: str | Path, max_vocab: int = 50000) -> None:
        """Build word vocabulary from text/code corpus."""
        corpus_file = Path(corpus_path)
        if not corpus_file.exists():
            raise FileNotFoundError(f"Corpus file not found: {corpus_file}")

        log.info("building_word_vocab", corpus=str(corpus_file), max_vocab=max_vocab)
        freq: dict[str, int] = {}

        with open(corpus_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    text = data.get("text", "")
                    tokens = _TOKEN_REGEX.findall(text)
                    for tok in tokens:
                        freq[tok] = freq.get(tok, 0) + 1
                except Exception:
                    # Plain text line fallback
                    tokens = _TOKEN_REGEX.findall(line)
                    for tok in tokens:
                        freq[tok] = freq.get(tok, 0) + 1

        # Sort by frequency
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        
        # Fill vocab starting after special tokens
        curr_idx = len(ENGLISH_SPECIAL_TOKENS)
        for word, count in sorted_words:
            if curr_idx >= max_vocab:
                break
            if word not in self.word2idx:
                self.word2idx[word] = curr_idx
                self.idx2word[curr_idx] = word
                curr_idx += 1

        self.vocab_size = len(self.word2idx)
        log.info("word_vocab_built", vocab_size=self.vocab_size)

    def save(self, model_dir: str | Path = "data/tokenizer") -> None:
        out_dir = Path(model_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        save_path = out_dir / "natural_word_vocab.json"

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"word2idx": self.word2idx, "idx2word": self.idx2word}, f, ensure_ascii=False, indent=2)
        log.info("word_vocab_saved", path=str(save_path))

    def load(self, model_dir: str | Path = "data/tokenizer") -> None:
        path = Path(model_dir) / "natural_word_vocab.json"
        if not path.exists():
            raise FileNotFoundError(f"Vocabulary file not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.word2idx = data["word2idx"]
            self.idx2word = {int(k): v for k, v in data["idx2word"].items()}
        self.vocab_size = len(self.word2idx)
        log.info("word_vocab_loaded", vocab_size=self.vocab_size)

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        tokens = _TOKEN_REGEX.findall(text)
        unk_idx = self.word2idx["<unk>"]
        ids = [self.word2idx.get(t, unk_idx) for t in tokens]
        
        if add_special_tokens:
            bos_idx = self.word2idx["<s>"]
            eos_idx = self.word2idx["</s>"]
            ids = [bos_idx] + ids + [eos_idx]
        return ids

    def decode(self, ids: Sequence[int], skip_special_tokens: bool = True) -> str:
        words = []
        special_ids = {self.word2idx[t] for t in ENGLISH_SPECIAL_TOKENS if t in self.word2idx}
        
        for idx in ids:
            if skip_special_tokens and idx in special_ids:
                continue
            words.append(self.idx2word.get(idx, "<unk>"))
            
        # Reconstruct natural spacing around words and punctuation
        text = ""
        for i, word in enumerate(words):
            if i > 0 and re.match(r"^\w+", word) and not text.endswith(("\n", " ", "(", "[")):
                text += " " + word
            else:
                text += word
        return text

    @property
    def pad_id(self) -> int:
        return self.word2idx["<pad>"]

    @property
    def bos_id(self) -> int:
        return self.word2idx["<s>"]

    @property
    def eos_id(self) -> int:
        return self.word2idx["</s>"]
