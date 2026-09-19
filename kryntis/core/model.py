"""
Kryntis Transformer Model — decoder-only architecture built in PyTorch with KV-Cache.

Implements a GPT-style causal language model with:
- Grouped-Query Attention (GQA) with KV-Cache support
- Rotary Positional Embeddings (RoPE)
- Pre-norm with RMSNorm (more stable than LayerNorm)
- SwiGLU feed-forward network
- Fast autoregressive inference via KVCache

Usage:
    cfg = KryntisModelConfig(vocab_size=260, n_layers=6, d_model=256)
    model = KryntisTransformer(cfg)
    logits, new_kvs = model(input_ids)
"""

from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass
class KryntisModelConfig:
    """Configuration for the Kryntis Transformer."""

    vocab_size: int = 260        # Direct UTF-8 byte vocab by default
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
    max_context_len: int = 2048

    def __post_init__(self) -> None:
        if self.max_context_len and not self.context_length:
            self.context_length = self.max_context_len
        assert self.d_model % self.n_heads == 0, "d_model must be divisible by n_heads"
        assert self.n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads


# Aliases for compatibility
ModelConfig = KryntisModelConfig


# ─── KV Cache ─────────────────────────────────────────────────────────────────

@dataclass
class KVCache:
    """
    Key-Value state cache for fast autoregressive decoding.
    Eliminates redundant prefix computation during incremental generation.
    """
    key: torch.Tensor    # (batch, n_kv_heads, seq_len, head_dim)
    value: torch.Tensor  # (batch, n_kv_heads, seq_len, head_dim)

    @property
    def seq_len(self) -> int:
        return self.key.shape[2]

    def update(self, new_k: torch.Tensor, new_v: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Append incoming key/value projections to the cached tensors."""
        self.key = torch.cat([self.key, new_k], dim=2)
        self.value = torch.cat([self.value, new_v], dim=2)
        return self.key, self.value


# ─── RMSNorm ──────────────────────────────────────────────────────────────────

class RMSNorm(nn.Module):
    """Root-mean-square layer normalisation (no learnable bias)."""

    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rms = x.pow(2).mean(-1, keepdim=True).add(self.eps).rsqrt()
        return x * rms * self.weight


# ─── Rotary Positional Embeddings ─────────────────────────────────────────────

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
    def rotate(x: torch.Tensor) -> torch.Tensor:
        xc = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
        xc = xc * freqs_cis.unsqueeze(0).unsqueeze(0)  # broadcast over batch, head
        return torch.view_as_real(xc).flatten(-2).type_as(x)

    return rotate(q), rotate(k)


# ─── Grouped-Query Attention ─────────────────────────────────────────────────

class GroupedQueryAttention(nn.Module):
    """
    Grouped-Query Attention (GQA) with dynamic KV-Cache support.
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
        kv_cache: Optional[KVCache | tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> tuple[torch.Tensor, KVCache]:
        B, T, _ = x.shape

        q = self.wq(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.wk(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.wv(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)

        # Apply RoPE
        q, k = _apply_rope(q, k, freqs_cis)

        # Update or initialise KV cache
        if kv_cache is not None:
            if isinstance(kv_cache, KVCache):
                k, v = kv_cache.update(k, v)
                new_cache = kv_cache
            else:
                pk, pv = kv_cache
                k = torch.cat([pk, k], dim=2)
                v = torch.cat([pv, v], dim=2)
                new_cache = KVCache(key=k, value=v)
        else:
            new_cache = KVCache(key=k, value=v)

        # Expand KV heads to match query heads
        k_expanded = k.repeat_interleave(self.kv_groups, dim=1)
        v_expanded = v.repeat_interleave(self.kv_groups, dim=1)

        # Scaled dot-product attention
        is_causal = (mask is None) and (T > 1) and (k.shape[2] == T)
        attn_out = F.scaled_dot_product_attention(
            q, k_expanded, v_expanded,
            attn_mask=mask,
            dropout_p=self.dropout.p if self.training else 0.0,
            is_causal=is_causal,
        )

        attn_out = attn_out.transpose(1, 2).contiguous().view(B, T, -1)
        return self.wo(attn_out), new_cache


# ─── SwiGLU Feed-Forward ─────────────────────────────────────────────────────

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


# ─── Transformer Block ───────────────────────────────────────────────────────

class TransformerBlock(nn.Module):
    """Single pre-norm transformer decoder block with KV-Cache."""

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
        kv_cache: Optional[KVCache | tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> tuple[torch.Tensor, KVCache]:
        attn_out, new_cache = self.attn(self.attn_norm(x), freqs_cis, mask, kv_cache)
        x = x + attn_out
        x = x + self.ffn(self.ffn_norm(x))
        return x, new_cache


# ─── Full Transformer ────────────────────────────────────────────────────────

class KryntisTransformer(nn.Module):
    """
    Kryntis decoder-only Transformer language model.
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
        kv_caches: Optional[list[KVCache]] = None,
        return_logits: bool = True,
    ) -> tuple[torch.Tensor, list[KVCache]]:
        """
        Forward pass with optional KV cache for accelerated decoding.

        Args:
            input_ids: (batch, seq_len) token IDs.
            kv_caches: Optional list of KVCache per layer from previous steps.
            return_logits: If True return logits else embeddings.

        Returns:
            (logits or embeddings, updated_kv_caches)
        """
        B, T = input_ids.shape
        offset = 0 if not kv_caches else kv_caches[0].seq_len

        x = self.dropout(self.embedding(input_ids))
        freqs = self.freqs_cis[offset: offset + T]

        new_caches: list[KVCache] = []
        for i, block in enumerate(self.blocks):
            cache_i = kv_caches[i] if kv_caches and i < len(kv_caches) else None
            x, updated_cache = block(x, freqs, kv_cache=cache_i)
            new_caches.append(updated_cache)

        x = self.norm(x)
        if return_logits:
            return self.lm_head(x), new_caches
        return x, new_caches

    def generate_with_cache(
        self,
        prompt_ids: torch.Tensor,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> torch.Tensor:
        """
        Fast autoregressive token generation using KV-cache.
        """
        self.eval()
        generated = prompt_ids.clone()
        kv_caches: list[KVCache] | None = None

        with torch.no_grad():
            # Prefill phase
            logits, kv_caches = self.forward(prompt_ids, kv_caches=None)
            next_token_logits = logits[:, -1, :] / max(1e-5, temperature)
            next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
            generated = torch.cat([generated, next_token], dim=1)

            # Incremental decode phase using cached KV states
            for _ in range(max_new_tokens - 1):
                logits, kv_caches = self.forward(next_token, kv_caches=kv_caches)
                next_token_logits = logits[:, -1, :] / max(1e-5, temperature)
                next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
                generated = torch.cat([generated, next_token], dim=1)

        return generated

    def get_loss(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Compute cross-entropy language modelling loss."""
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
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), str(p) + ".pt")
        with open(str(p) + ".config.json", "w") as f:
            json.dump(dataclasses.asdict(self.cfg), f, indent=2)
        log.info("model_checkpoint_saved", path=path)

    @classmethod
    def load_checkpoint(cls, path: str) -> KryntisTransformer:
        """Load model from checkpoint."""
        p = Path(path)
        with open(str(p) + ".config.json") as f:
            cfg_dict = json.load(f)
        cfg = KryntisModelConfig(**cfg_dict)
        model = cls(cfg)
        model.load_state_dict(torch.load(str(p) + ".pt", map_location="cpu"))
        log.info("model_checkpoint_loaded", path=path, params=model.num_parameters())
        return model


DecoderTransformer = KryntisTransformer
