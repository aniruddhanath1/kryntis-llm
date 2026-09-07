"""
Training Evaluator — Calculates perplexity on held-out evaluation datasets.
"""

from __future__ import annotations

import math
from pathlib import Path

import torch
import torch.nn as nn

from kryntis.core.model import DecoderTransformer, ModelConfig
from kryntis.core.tokenizer import CodeBPETokenizer
from kryntis.training.config import TrainingConfig
from kryntis.training.dataset_loader import create_dataloader
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class TrainingEvaluator:
    """Evaluates trained model checkpoints."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.cfg = config or TrainingConfig()
        self.device = torch.device(self.cfg.device if torch.cuda.is_available() else "cpu")
        from kryntis.core.word_tokenizer import NaturalEnglishTokenizer

        self.tokenizer = NaturalEnglishTokenizer()
        self.tokenizer.load()

        self.cfg.vocab_size = self.tokenizer.vocab_size

        model_cfg = ModelConfig(
            vocab_size=self.cfg.vocab_size,
            context_length=self.cfg.max_seq_len,
            n_layers=self.cfg.n_layers,
            n_heads=self.cfg.n_heads,
            d_model=self.cfg.d_model,
            d_ff=self.cfg.d_ff,
        )

        self.model = DecoderTransformer(model_cfg).to(self.device)
        self.criterion = nn.CrossEntropyLoss()

    def evaluate_checkpoint(self, checkpoint_path: str | Path) -> dict[str, float]:
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")

        log.info("evaluating_checkpoint", path=str(path))
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        dataloader = create_dataloader(
            self.cfg.data_path,
            self.tokenizer,
            batch_size=self.cfg.batch_size,
            max_seq_len=self.cfg.max_seq_len,
        )

        total_loss = 0.0
        total_batches = 0
        max_eval_batches = 200

        with torch.no_grad():
            for i, batch in enumerate(dataloader):
                if i >= max_eval_batches:
                    break
                x = batch["input_ids"].to(self.device)
                y = batch["labels"].to(self.device)

                logits = self.model(x)
                loss = self.criterion(logits.view(-1, self.cfg.vocab_size), y.view(-1))
                total_loss += loss.item()
                total_batches += 1

        avg_loss = total_loss / max(total_batches, 1)
        perplexity = math.exp(min(avg_loss, 20))

        log.info("evaluation_completed", loss=round(avg_loss, 4), perplexity=round(perplexity, 2))
        return {"loss": avg_loss, "perplexity": perplexity}
