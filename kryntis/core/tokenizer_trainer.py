"""
Tokenizer Trainer — Trains a Byte-Level BPE Tokenizer on the cleaned code corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

from kryntis.core.tokenizer import CODE_SPECIAL_TOKENS
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class TokenizerTrainer:
    """
    Trains a byte-level BPE tokenizer on processed JSONL files.
    """

    def __init__(self, vocab_size: int = 32000) -> None:
        self.vocab_size = vocab_size

    def train_from_corpus(
        self,
        corpus_path: str | Path = "data/processed/train_corpus.jsonl",
        output_dir: str | Path = "data/tokenizer",
    ) -> Path:
        corpus_file = Path(corpus_path)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if not corpus_file.exists():
            raise FileNotFoundError(f"Corpus file not found: {corpus_file}")

        log.info("start_tokenizer_training", corpus=str(corpus_file), vocab_size=self.vocab_size)

        from tokenizers import Tokenizer, decoders, models, normalizers, pre_tokenizers, trainers

        # 1. Byte-level BPE Model
        tokenizer = Tokenizer(models.BPE(unk_token="<unk>"))
        tokenizer.normalizer = normalizers.Sequence([])
        tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tokenizer.decoder = decoders.ByteLevel()

        # 2. BPE Trainer
        trainer = trainers.BpeTrainer(
            vocab_size=self.vocab_size,
            special_tokens=CODE_SPECIAL_TOKENS,
            min_frequency=2,
            show_progress=True,
        )

        # 3. Iterator over file to save memory
        def file_iterator():
            with open(corpus_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        text = data.get("text", "")
                        if text:
                            yield text
                    except Exception:
                        continue

        tokenizer.train_from_iterator(file_iterator(), trainer=trainer)

        save_path = out_dir / "tokenizer.json"
        tokenizer.save(str(save_path))
        log.info("tokenizer_training_completed", saved_path=str(save_path))
        return save_path
