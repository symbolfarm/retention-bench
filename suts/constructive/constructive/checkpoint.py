"""Checkpoint persistence for the constructive SUT.

RESET = SIGKILL with no shutdown hook (see docs/sut-interface.md). Anything
that must survive a RESET has to be on disk *before* the response to the event
preceding the RESET is written. So we flush a full checkpoint to DIR on every
READ, before writing the READ ack.

A checkpoint is a single `torch.save` blob containing:
  - `config`:   the (possibly grown) ModelConfig as a dict — read first so a
                fresh process rebuilds the right shape before load_state_dict.
  - `model`:    state_dict of the current (grown) model.
  - `meta`:     training bookkeeping (train_steps, growth_count, seed, etc.)
                that the SUT self-reports via the `notes` field.

The architecture config travels *with* the weights precisely because growth
makes the reloaded shape differ from a default model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import torch

from .model import ByteTransformer, ModelConfig, build_model

CHECKPOINT_NAME = "checkpoint.pt"


@dataclass
class Meta:
    train_steps: int = 0
    train_flops: int = 0
    growth_count: int = 0
    read_count: int = 0
    seed: int = 0

    def to_dict(self) -> dict:
        return {
            "train_steps": self.train_steps,
            "train_flops": self.train_flops,
            "growth_count": self.growth_count,
            "read_count": self.read_count,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Meta":
        return cls(
            train_steps=int(d.get("train_steps", 0)),
            train_flops=int(d.get("train_flops", 0)),
            growth_count=int(d.get("growth_count", 0)),
            read_count=int(d.get("read_count", 0)),
            seed=int(d.get("seed", 0)),
        )


@dataclass
class State:
    """In-memory SUT state: the model + its bookkeeping."""

    model: ByteTransformer
    config: ModelConfig
    meta: Meta = field(default_factory=Meta)


def checkpoint_path(dir_path: Path) -> Path:
    return dir_path / CHECKPOINT_NAME


def has_checkpoint(dir_path: Path) -> bool:
    return checkpoint_path(dir_path).is_file()


def save(dir_path: Path, state: State) -> None:
    """Atomically flush the full checkpoint to DIR.

    Write to a temp file in the same directory, then os.replace — so a RESET
    that interrupts the write can never leave a half-written checkpoint.
    """
    path = checkpoint_path(dir_path)
    tmp = path.with_suffix(".pt.tmp")
    blob = {
        "config": state.config.to_dict(),
        "model": state.model.state_dict(),
        "meta": state.meta.to_dict(),
    }
    torch.save(blob, tmp)
    tmp.replace(path)


def load(dir_path: Path) -> State:
    """Rebuild the grown architecture from the saved config, then load weights.

    `weights_only=False` is used because the blob holds plain dicts (config /
    meta) alongside tensors. Source is the SUT's own DIR, written by a prior
    session of this same SUT — not untrusted input.
    """
    path = checkpoint_path(dir_path)
    blob = torch.load(path, map_location="cpu", weights_only=False)
    config = ModelConfig.from_dict(blob["config"])
    meta = Meta.from_dict(blob.get("meta", {}))
    model = build_model(config, seed=meta.seed)
    model.load_state_dict(blob["model"])
    return State(model=model, config=config, meta=meta)


def cold_init(config: ModelConfig, seed: int = 0) -> State:
    """Fresh model for an empty DIR (first session of a run)."""
    model = build_model(config, seed=seed)
    return State(model=model, config=config, meta=Meta(seed=seed))
