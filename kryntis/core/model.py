"""
Kryntis Transformer Model — decoder-only architecture built in PyTorch.

Implements a GPT-style causal language model with:
- Multi-head causal self-attention (with RoPE positional encoding)
- Pre-norm with RMSNorm (more stable than LayerNorm)
- SwiGLU feed-forward network
- Configurable depth, width, heads, context length

This is the *custom* Kryntis model architecture, separate from the
downloaded base model. It can be fine-tuned on specific domains.

Usage:
    cfg = KryntisModelConfig(vocab_size=8000, n_layers=6, d_model=256)
    model = KryntisTransformer(cfg)
    logits = model(input_ids)         # (batch, seq_len, vocab_size)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


# ─── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class KryntisModelConfig:
    """Configuration for the Kryntis Transformer."""

    vocab_size: int = 8000
    n_layers: int = 6
    d_model: int = 256           # Embedding dimension
    n_heads: int = 8             # Attention heads
    n_kv_heads: int = 4          # KV heads (grouped-query attention)
    d_ff: int = 768              # Feed-forward hidden dim (≈ 3 × d_model)
    context_length: int = 2048
    dropout: float = 0.1
    rope_base: int = 10000
    tie_embeddings: bool = True  # Tie input/output embeddings
    norm_eps: float = 1e-6
    pad_token_id: int = 0

    def __post_init__(self) -> None:
        assert self.d_model % self.n_heads == 0, "d_model must be divisible by n_heads"
        assert self.n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads


# Aliases for compatibility
ModelConfig = KryntisModelConfig


# ─── RMSNorm ────────────────────────────────────────────────────────────────────

class RMSNorm(nn.Module):
    """Root-mean-square layer normalisation (no learnable bias)."""

    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rms = x.pow(2).mean(-1, keepdim=True).add(self.eps).rsqrt()
        return x * rms * self.weight


# ─── Rotary Positional Embeddings ───────────────────────────────────────────────

def _precompute_freqs(head_dim: int, context_length: int, base: int = 10000) -> torch.Tensor:
    """Precompute RoPE frequency cis tensor."""
    theta = 1.0 / (base ** (torch.arange(0, head_dim, 2).float() / head_dim))
    positions = torch.arange(context_length).float()
    freqs = torch.outer(positions, theta)  # (seq, head_dim/2)
    return torch.polar(torch.ones_like(freqs), freqs)  # complex


def _apply_rope(
    q: torch.Tensor, k: torch.Tensor, freqs_cis: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """Apply rotary positional embeddings to Q and K."""
    # q, k: (batch, heads, seq, head_dim)
    # Cast to complex for rotation
    def rotate(x: torch.Tensor) -> torch.Tensor:
        xc = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
        xc = xc * freqs_cis.unsqueeze(0).unsqueeze(0)  # broadcast over batch, head
        return torch.view_as_real(xc).flatten(-2).type_as(x)

    return rotate(q), rotate(k)


# ─── Grouped-Query Attention ─────────────────────────────────────────────────────

class GroupedQueryAttention(nn.Module):
    """
    Grouped-Query Attention (GQA).

    n_kv_heads < n_heads shares KV projections across groups of query heads,
    reducing memory during inference.
    """

    def __init__(self, cfg: KryntisModelConfig) -> None:
        super().__init__()
        self.n_heads = cfg.n_heads
        self.n_kv_heads = cfg.n_kv_heads
        self.head_dim = cfg.head_dim
        self.kv_groups = cfg.n_heads // cfg.n_kv_heads

        self.wq = nn.Linear(cfg.d_model, cfg.n_heads * cfg.head_dim, bias=False)
        self.wk = nn.Linear(cfg.d_model, cfg.n_kv_heads * cfg.head_dim, bias=False)
        self.wv = nn.Linear(cfg.d_model, cfg.n_kv_heads * cfg.head_dim, bias=False)
        self.wo = nn.Linear(cfg.n_heads * cfg.head_dim, cfg.d_model, bias=False)

        self.dropout = nn.Dropout(cfg.dropout)
        self.scale = self.head_dim ** -0.5

    def forward(
        self,
        x: torch.Tensor,
        freqs_cis: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        past_kv: Optional[tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        B, T, _ = x.shape

        q = self.wq(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.wk(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.wv(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)

        # Apply RoPE
        q, k = _apply_rope(q, k, freqs_cis)

        # KV cache support
        if past_kv is not None:
            pk, pv = past_kv
            k = torch.cat([pk, k], dim=2)
            v = torch.cat([pv, v], dim=2)
        new_kv = (k, v)

        # Expand KV heads to match query heads
        k = k.repeat_interleave(self.kv_groups, dim=1)
        v = v.repeat_interleave(self.kv_groups, dim=1)

        # Scaled dot-product attention (uses flash attention if available)
        attn_out = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=mask,
            dropout_p=self.dropout.p if self.training else 0.0,
            is_causal=(mask is None),
        )

        attn_out = attn_out.transpose(1, 2).contiguous().view(B, T, -1)
        return self.wo(attn_out), new_kv


# ─── SwiGLU Feed-Forward ────────────────────────────────────────────────────────

class SwiGLUFFN(nn.Module):
    """SwiGLU feed-forward: FFN(x) = SiLU(xW₁) ⊙ (xW₃) · W₂"""

    def __init__(self, cfg: KryntisModelConfig) -> None:
        super().__init__()
        self.w1 = nn.Linear(cfg.d_model, cfg.d_ff, bias=False)
        self.w2 = nn.Linear(cfg.d_ff, cfg.d_model, bias=False)
        self.w3 = nn.Linear(cfg.d_model, cfg.d_ff, bias=False)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))


# ─── Transformer Block ──────────────────────────────────────────────────────────

class TransformerBlock(nn.Module):
    """Single pre-norm transformer decoder block."""

    def __init__(self, cfg: KryntisModelConfig) -> None:
        super().__init__()
        self.attn_norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.attn = GroupedQueryAttention(cfg)
        self.ffn_norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.ffn = SwiGLUFFN(cfg)

    def forward(
        self,
        x: torch.Tensor,
        freqs_cis: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        past_kv: Optional[tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        attn_out, new_kv = self.attn(self.attn_norm(x), freqs_cis, mask, past_kv)
        x = x + attn_out
        x = x + self.ffn(self.ffn_norm(x))
        return x, new_kv


# ─── Full Transformer ────────────────────────────────────────────────────────────

class KryntisTransformer(nn.Module):
    """
    Kryntis decoder-only Transformer language model.

    Parameters are approximately:
        6L-256d-8h  → ~10M params  (default, ultra-lightweight)
        12L-512d-8h → ~85M params  (medium)
        24L-768d-12h → ~350M params (large)
    """

    def __init__(self, cfg: KryntisModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.embedding = nn.Embedding(cfg.vocab_size, cfg.d_model, padding_idx=cfg.pad_token_id)
        self.dropout = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList([TransformerBlock(cfg) for _ in range(cfg.n_layers)])
        self.norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)

        if cfg.tie_embeddings:
            self.lm_head.weight = self.embedding.weight

        # Precompute RoPE frequencies
        freqs = _precompute_freqs(cfg.head_dim, cfg.context_length, cfg.rope_base)
        self.register_buffer("freqs_cis", freqs, persistent=False)

        self._init_weights()
        n_params = sum(p.numel() for p in self.parameters())
        log.info("model_initialised", params=f"{n_params/1e6:.2f}M", config=cfg)

    def _init_weights(self) -> None:
        """GPT-style weight initialisation."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        past_kvs: Optional[list[tuple[torch.Tensor, torch.Tensor]]] = None,
        return_logits: bool = True,
    ) -> tuple[torch.Tensor, list[tuple[torch.Tensor, torch.Tensor]]]:
        """
        Forward pass.

        Args:
            input_ids: (batch, seq_len) token IDs.
            past_kvs: Optional KV cache from previous steps.
            return_logits: If True return logits else embeddings.

        Returns:
            (logits or embeddings, new_kvs)
        """
        B, T = input_ids.shape
        offset = 0 if past_kvs is None else past_kvs[0][0].size(2)

        x = self.dropout(self.embedding(input_ids))
        freqs = self.freqs_cis[offset: offset + T]

        new_kvs: list[tuple[torch.Tensor, torch.Tensor]] = []
        for i, block in enumerate(self.blocks):
            pkv = past_kvs[i] if past_kvs else None
            x, kv = block(x, freqs, past_kv=pkv)
            new_kvs.append(kv)

        x = self.norm(x)
        if return_logits:
            return self.lm_head(x), new_kvs
        return x, new_kvs

    def get_loss(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute cross-entropy language modelling loss.

        Args:
            input_ids: (batch, seq) input tokens.
            labels: (batch, seq) target tokens. If None, uses shifted input_ids.

        Returns:
            Scalar loss tensor.
        """
        logits, _ = self.forward(input_ids)
        if labels is None:
            labels = torch.roll(input_ids, -1, dims=1)
            labels[:, -1] = self.cfg.pad_token_id

        loss = F.cross_entropy(
            logits.view(-1, self.cfg.vocab_size),
            labels.view(-1),
            ignore_index=self.cfg.pad_token_id,
        )
        return loss

    def num_parameters(self, trainable_only: bool = False) -> int:
        if trainable_only:
            return sum(p.numel() for p in self.parameters() if p.requires_grad)
        return sum(p.numel() for p in self.parameters())

    def save_checkpoint(self, path: str) -> None:
        """Save model weights and config."""
        import json
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), str(p) + ".pt")
        with open(str(p) + ".config.json", "w") as f:
            import dataclasses
            json.dump(dataclasses.asdict(self.cfg), f, indent=2)
        log.info("model_checkpoint_saved", path=path)

    @classmethod
    def load_checkpoint(cls, path: str) -> "KryntisTransformer":
        """Load model from checkpoint."""
        import json
        import dataclasses
        from pathlib import Path
        p = Path(path)
        with open(str(p) + ".config.json") as f:
            cfg_dict = json.load(f)
        cfg = KryntisModelConfig(**cfg_dict)
        model = cls(cfg)
        model.load_state_dict(torch.load(str(p) + ".pt", map_location="cpu"))
        log.info("model_checkpoint_loaded", path=path, params=model.num_parameters())
        return model


DecoderTransformer = KryntisTransformer
