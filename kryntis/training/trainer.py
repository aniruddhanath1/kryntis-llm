"""
Trainer — Pretraining loop for Kryntis Coder transformer model.
"""

from __future__ import annotations

import math
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import AdamW

from kryntis.core.model import DecoderTransformer, ModelConfig
from kryntis.core.tokenizer import CodeBPETokenizer
from kryntis.training.config import TrainingConfig
from kryntis.training.dataset_loader import create_dataloader
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class Trainer:
    """
    Main Pretraining Engine. Supports gradient accumulation,
    checkpointing, and resuming training.
    """

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.cfg = config or TrainingConfig()
        self.ckpt_dir = Path(self.cfg.checkpoint_dir)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)

        from kryntis.core.byte_processor import ByteDirectProcessor
        from kryntis.core.word_tokenizer import NaturalEnglishTokenizer

        # Use Direct Byte / ASCII processor (Tokenizer-Free) by default
        self.tokenizer = ByteDirectProcessor()

        self.cfg.vocab_size = self.tokenizer.vocab_size

        model_cfg = ModelConfig(
            vocab_size=self.cfg.vocab_size,
            context_length=self.cfg.max_seq_len,
            n_layers=self.cfg.n_layers,
            n_heads=self.cfg.n_heads,
            d_model=self.cfg.d_model,
            d_ff=self.cfg.d_ff,
            dropout=self.cfg.dropout,
        )

        self.device = torch.device(self.cfg.device if torch.cuda.is_available() else "cpu")
        self.model = DecoderTransformer(model_cfg).to(self.device)
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=self.cfg.learning_rate,
            weight_decay=self.cfg.weight_decay,
        )
        self.criterion = nn.CrossEntropyLoss()

        self.step = 0

    def train(self, resume: bool = False, domain: str | None = None) -> None:
        if resume:
            self._load_latest_checkpoint()

        data_path = f"data/processed/train_corpus_{domain}.jsonl" if domain else self.cfg.data_path

        log.info(
            "start_training",
            device=str(self.device),
            domain=domain or "all",
            data_path=data_path,
            batch_size=self.cfg.batch_size,
            grad_accum=self.cfg.grad_accum_steps,
            step=self.step,
        )

        dataloader = create_dataloader(
            data_path,
            self.tokenizer,
            batch_size=self.cfg.batch_size,
            max_seq_len=self.cfg.max_seq_len,
        )

        self.model.train()
        self.optimizer.zero_grad()

        accumulated_loss = 0.0
        start_time = time.time()

        for batch in dataloader:
            x = batch["input_ids"].to(self.device)
            y = batch["labels"].to(self.device)

            logits, _ = self.model(x)
            loss = self.criterion(logits.view(-1, self.cfg.vocab_size), y.view(-1))
            loss = loss / self.cfg.grad_accum_steps
            loss.backward()

            accumulated_loss += loss.item() * self.cfg.grad_accum_steps

            if (self.step + 1) % self.cfg.grad_accum_steps == 0:
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                self.optimizer.zero_grad()

                actual_step = (self.step + 1) // self.cfg.grad_accum_steps

                if actual_step % self.cfg.log_every_steps == 0:
                    elapsed = time.time() - start_time
                    log.info(
                        "training_progress",
                        step=actual_step,
                        loss=round(accumulated_loss, 4),
                        perplexity=round(math.exp(min(accumulated_loss, 20)), 2),
                        sec_per_log=round(elapsed, 2),
                    )
                    start_time = time.time()

                if actual_step % self.cfg.save_every_steps == 0:
                    self._save_checkpoint(actual_step)

                if actual_step >= self.cfg.max_steps:
                    log.info("max_training_steps_reached", step=actual_step)
                    break

            self.step += 1

        self._save_checkpoint((self.step + 1) // self.cfg.grad_accum_steps, final=True)
        log.info("training_finished")

    def _save_checkpoint(self, step: int, final: bool = False) -> None:
        filename = "final_model.pt" if final else f"checkpoint_step_{step}.pt"
        path = self.ckpt_dir / filename
        checkpoint = {
            "step": step,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
        }
        torch.save(checkpoint, path)
        log.info("checkpoint_saved", path=str(path), step=step)

    def _load_latest_checkpoint(self) -> None:
        checkpoints = sorted(self.ckpt_dir.glob("checkpoint_step_*.pt"))
        if not checkpoints:
            log.warning("no_checkpoint_found_starting_fresh")
            return

        latest = checkpoints[-1]
        log.info("loading_checkpoint", path=str(latest))
        checkpoint = torch.load(latest, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.step = checkpoint["step"] * self.cfg.grad_accum_steps
