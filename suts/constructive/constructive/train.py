"""Bounded next-token training on READ text.

A *few* gradient steps per READ — NOT train-to-convergence. This is the honest
continual-learning shape (the model never gets to fully fit any one chapter)
and keeps each READ well inside the 300s/event timeout on CPU.
"""

from __future__ import annotations

import torch

from .checkpoint import State
from .model import ByteTransformer, ModelConfig

# Bounded training budget per READ. Small enough to be fast on CPU.
STEPS_PER_READ = 8
LEARNING_RATE = 3e-3


def _windows(ids: list[int], block_size: int) -> list[list[int]]:
    """Slice ids into non-overlapping (block_size + 1)-length windows.

    Each window yields an (input, target) pair of length block_size. Drops a
    trailing remainder shorter than 2 tokens.
    """
    span = block_size + 1
    out: list[list[int]] = []
    for start in range(0, max(1, len(ids) - 1), block_size):
        chunk = ids[start : start + span]
        if len(chunk) >= 2:
            out.append(chunk)
    return out


def _approx_flops(model: ByteTransformer, n_steps: int, n_tokens: int) -> int:
    """Very rough train-FLOPs estimate: ~6 * params * tokens (fwd+bwd)."""
    return 6 * model.param_count() * n_steps * max(1, n_tokens)


def train_on_text(state: State, ids: list[int]) -> int:
    """Run a bounded number of gradient steps on the READ text.

    Mutates `state.model` weights in place and bumps `state.meta` counters.
    Returns the number of gradient steps actually taken.
    """
    model = state.model
    cfg: ModelConfig = state.config
    windows = _windows(ids, cfg.block_size)
    if not windows:
        return 0

    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    steps = 0
    tokens_seen = 0
    for step in range(STEPS_PER_READ):
        window = windows[step % len(windows)]
        x = torch.tensor([window[:-1]], dtype=torch.long)
        y = torch.tensor([window[1:]], dtype=torch.long)
        opt.zero_grad()
        _, loss = model(x, y)
        loss.backward()
        opt.step()
        steps += 1
        tokens_seen += x.numel()

    state.meta.train_steps += steps
    state.meta.train_flops += _approx_flops(model, steps, tokens_seen // max(1, steps))
    return steps


@torch.no_grad()
def lm_loss(state: State, ids: list[int]) -> float:
    """Mean next-token loss over `ids` — used by tests to show retention."""
    model = state.model
    cfg = state.config
    windows = _windows(ids, cfg.block_size)
    if not windows:
        return float("nan")
    model.eval()
    total = 0.0
    for window in windows:
        x = torch.tensor([window[:-1]], dtype=torch.long)
        y = torch.tensor([window[1:]], dtype=torch.long)
        _, loss = model(x, y)
        total += float(loss.item())
    return total / len(windows)
