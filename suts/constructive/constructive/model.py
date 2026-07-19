"""Tiny from-scratch byte-level transformer for the constructive SUT.

Deliberately minimal: a stack of pre-norm transformer blocks over a 256-symbol
byte vocabulary (plus one BOS symbol = id 256). The point is the *integration
seam*, not model quality. Everything here is CPU-only,
offline, and deterministic given a fixed seed.

The architecture is described entirely by a `ModelConfig` dataclass that is
serialised into the checkpoint alongside the weights. A growth event mutates
the config (e.g. adds a block); a fresh process rebuilds the *grown* shape from
the saved config *before* `load_state_dict`, so a variable-size checkpoint
round-trips correctly across RESET.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# Byte vocabulary: 256 raw byte values + 1 BOS marker.
BOS = 256
VOCAB_SIZE = 257


@dataclass
class ModelConfig:
    """Serialisable description of the (possibly grown) architecture.

    Stored in the checkpoint so a fresh process can rebuild the exact shape
    before loading weights. `n_layers` is the field a growth event mutates.
    """

    vocab_size: int = VOCAB_SIZE
    block_size: int = 64
    d_model: int = 64
    n_heads: int = 4
    n_layers: int = 2

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ModelConfig":
        # Tolerate extra/missing keys so old checkpoints still load.
        fields = {f for f in cls().to_dict()}
        return cls(**{k: v for k, v in d.items() if k in fields})


class Block(nn.Module):
    """Pre-norm transformer block: causal self-attention + MLP."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(cfg.d_model)
        self.attn = nn.MultiheadAttention(
            cfg.d_model, cfg.n_heads, batch_first=True
        )
        self.ln2 = nn.LayerNorm(cfg.d_model)
        self.mlp = nn.Sequential(
            nn.Linear(cfg.d_model, 4 * cfg.d_model),
            nn.GELU(),
            nn.Linear(4 * cfg.d_model, cfg.d_model),
        )

    def forward(self, x: torch.Tensor, attn_mask: torch.Tensor) -> torch.Tensor:
        h = self.ln1(x)
        a, _ = self.attn(h, h, h, attn_mask=attn_mask, need_weights=False)
        x = x + a
        x = x + self.mlp(self.ln2(x))
        return x


class ByteTransformer(nn.Module):
    """Minimal causal LM over the byte vocabulary."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.pos_emb = nn.Embedding(cfg.block_size, cfg.d_model)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layers))
        self.ln_f = nn.LayerNorm(cfg.d_model)
        self.head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)

    def forward(
        self, idx: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        _, t = idx.shape
        pos = torch.arange(t, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)[None, :, :]
        # Causal mask: True = disallowed (per nn.MultiheadAttention bool mask).
        mask = torch.triu(
            torch.ones(t, t, dtype=torch.bool, device=idx.device), diagonal=1
        )
        for block in self.blocks:
            x = block(x, mask)
        x = self.ln_f(x)
        logits = self.head(x)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), targets.reshape(-1)
            )
        return logits, loss

    def param_count(self) -> int:
        return sum(p.numel() for p in self.parameters())

    @torch.no_grad()
    def generate(
        self, prompt_ids: list[int], max_new_tokens: int, temperature: float = 0.0
    ) -> list[int]:
        """Greedy (temperature=0) or sampled byte-level continuation.

        Quality is a non-goal; this just exercises generation from current
        weights. Stops early on a newline byte to keep answers short.
        """
        self.eval()
        device = next(self.parameters()).device
        ids = list(prompt_ids)
        out: list[int] = []
        for _ in range(max_new_tokens):
            window = ids[-self.cfg.block_size :]
            x = torch.tensor([window], dtype=torch.long, device=device)
            logits, _ = self(x)
            logits = logits[0, -1, :]
            if temperature <= 0.0:
                nxt = int(torch.argmax(logits).item())
            else:
                probs = F.softmax(logits / temperature, dim=-1)
                nxt = int(torch.multinomial(probs, num_samples=1).item())
            if nxt == BOS:
                break
            ids.append(nxt)
            out.append(nxt)
            if nxt == ord("\n"):
                break
        return out


def grow(cfg: ModelConfig, model: ByteTransformer) -> ByteTransformer:
    """Add one transformer block, preserving learned weights.

    Builds a model with `n_layers + 1`, copies the existing blocks' state in,
    and leaves the new (final) block freshly initialised. The new block starts
    near-identity-ish only insofar as residual connections mean an untrained
    block still passes signal through; quality is not the point — the point is
    `storage-delta > 0` and a checkpoint whose shape differs from the default.
    """
    new_cfg = ModelConfig(**{**cfg.to_dict(), "n_layers": cfg.n_layers + 1})
    new_model = ByteTransformer(new_cfg)
    # Copy everything except the (now longer) block list, then copy the old
    # blocks one-for-one into the front of the new stack.
    old_sd = model.state_dict()
    new_sd = new_model.state_dict()
    for k, v in old_sd.items():
        if k in new_sd and new_sd[k].shape == v.shape:
            new_sd[k] = v
    new_model.load_state_dict(new_sd)
    return new_model


def build_model(cfg: ModelConfig, seed: int = 0) -> ByteTransformer:
    """Construct a model deterministically from a config."""
    g = torch.Generator().manual_seed(seed)
    # Seed global RNG so default-initialised params are reproducible.
    torch.manual_seed(seed)
    model = ByteTransformer(cfg)
    del g
    return model


def text_to_ids(text: str) -> list[int]:
    """Byte-level encode: BOS then raw UTF-8 bytes."""
    return [BOS] + list(text.encode("utf-8"))
