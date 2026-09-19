"""
Training Configuration dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrainingConfig:
    # Model architecture (25M parameters, 8GB RAM safe)
    vocab_size: int = 32000
    d_model: int = 512
    n_layers: int = 12
    n_heads: int = 8
    d_ff: int = 2048
    max_seq_len: int = 256
    dropout: float = 0.1

    # Optimization
    batch_size: int = 2                # Physical batch size
    grad_accum_steps: int = 16          # Effective batch size = 32
    learning_rate: float = 3e-4
    min_lr: float = 3e-5
    weight_decay: float = 0.01
    max_steps: int = 50000
    warmup_steps: int = 1000

    # Paths and Checkpointing
    data_path: str = "data/processed/train_corpus.jsonl"
    checkpoint_dir: str = "data/models/checkpoints"
    save_every_steps: int = 1000
    log_every_steps: int = 50
    device: str = "cpu"                # "cpu" or "cuda"
