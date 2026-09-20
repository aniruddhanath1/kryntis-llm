"""
User Trainer — Enables continuous model fine-tuning directly from user inputs and feedback
with automated prompt-injection, delimiter-injection, and toxic-content screening.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from kryntis.security.guardrails import get_guardrail_pipeline
from kryntis.training.config import TrainingConfig
from kryntis.training.trainer import Trainer
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_PROHIBITED_SPECIAL_TOKENS = [
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
    "<s>",
    "</s>",
    "<pad>",
    "<unk>",
    "<sep>",
]


class UserTrainer:
    """
    Manages fine-tuning the model using direct user interactions and corrections with safety checks.
    """

    def __init__(
        self,
        user_corpus_path: str = "data/processed/train_corpus_user.jsonl",
        checkpoint_dir: str = "checkpoints/user_tuned",
    ) -> None:
        self.user_corpus_path = Path(user_corpus_path)
        self.user_corpus_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._guardrails = get_guardrail_pipeline()

    def record_user_sample(
        self,
        prompt: str,
        response: str,
        domain: str = "user_input",
    ) -> int:
        """
        Record a single prompt-response training pair from the user after security checks.

        Args:
            prompt: User input prompt or instruction.
            response: Expected or corrected AI response.
            domain: Domain tag.

        Returns:
            Total number of user training samples recorded so far.
        """
        prompt = prompt.strip()
        response = response.strip()
        if not prompt or not response:
            raise ValueError("Both prompt and response must be non-empty.")

        if len(prompt) > 8192 or len(response) > 8192:
            raise ValueError("Prompt or response exceeds maximum allowed length of 8192 characters.")

        # Check for control delimiter injections
        for token in _PROHIBITED_SPECIAL_TOKENS:
            if token in prompt or token in response:
                raise ValueError(f"Special control delimiter '{token}' is prohibited in training data.")

        # Run guardrail check on prompt
        guard_res = self._guardrails.check_input(prompt)
        if guard_res.blocked:
            raise ValueError(f"Training sample rejected by safety guardrails: {guard_res.reason}")

        formatted_text = f"User: {prompt}\nAssistant: {response}"
        record = {
            "domain": domain,
            "lang": "english",
            "text": formatted_text,
        }

        with open(self.user_corpus_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        total_samples = self.count_samples()
        log.info(
            "user_training_sample_recorded",
            prompt_len=len(prompt),
            response_len=len(response),
            total_user_samples=total_samples,
        )
        return total_samples

    def count_samples(self) -> int:
        """Count total user training samples in the corpus."""
        if not self.user_corpus_path.exists():
            return 0
        with open(self.user_corpus_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())

    def train_on_user_data(
        self,
        max_steps: int = 20,
        learning_rate: float = 1e-4,
        batch_size: int = 2,
    ) -> dict[str, Any]:
        """
        Execute incremental training steps on recorded user data.

        Args:
            max_steps: Maximum training steps.
            learning_rate: Learning rate for fine-tuning.
            batch_size: Micro-batch size.

        Returns:
            Training metrics summary dictionary.
        """
        samples_count = self.count_samples()
        if samples_count == 0:
            return {
                "status": "skipped",
                "reason": "No user samples found in corpus. Record samples before training.",
            }

        log.info("start_user_data_training", samples=samples_count, steps=max_steps)

        # Configure trainer for user corpus
        config = TrainingConfig()
        config.learning_rate = learning_rate
        config.batch_size = batch_size
        config.max_steps = max_steps
        config.data_path = str(self.user_corpus_path)
        config.checkpoint_dir = str(self.checkpoint_dir)

        try:
            trainer = Trainer(config=config)
            trainer.train()

            log.info("user_data_training_complete", samples=samples_count, steps=max_steps)
            return {
                "status": "success",
                "samples_trained": samples_count,
                "steps": max_steps,
                "checkpoint_dir": str(self.checkpoint_dir),
            }
        except Exception as e:
            log.error("user_data_training_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
            }
