"""Fake `anthropic` SDK shim for retention-bench integration tests.

Shadows the real `anthropic` package when its parent directory is prepended
to PYTHONPATH. Returns canned responses keyed by call sequence, loaded from
a YAML fixture pointed to by env var.

Env contract:
  FAKE_ANTHROPIC_FIXTURE  Path to YAML file with a `responses` list, each
                          entry having `text`, `input_tokens`, `output_tokens`.
  FAKE_ANTHROPIC_COUNTER  Path to a file storing the next call index as
                          ASCII int. Shared across SUT subprocesses within
                          a single test run; lets us prove that respawned
                          SUTs (after RESET) successfully imported this
                          shim and continued the sequence.

Out of scope: streaming, async, tool use, multi-turn, anything beyond
`client.messages.create(...)` with the small surface no-state SUT uses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class _Response:
    content: list[_TextBlock]
    usage: _Usage
    model: str


def _load_responses() -> list[dict[str, Any]]:
    path = os.environ.get("FAKE_ANTHROPIC_FIXTURE")
    if not path:
        raise RuntimeError("FAKE_ANTHROPIC_FIXTURE env var is not set")
    data = yaml.safe_load(Path(path).read_text())
    return data["responses"]


def _next_index() -> int:
    path = os.environ.get("FAKE_ANTHROPIC_COUNTER")
    if not path:
        raise RuntimeError("FAKE_ANTHROPIC_COUNTER env var is not set")
    p = Path(path)
    try:
        i = int(p.read_text().strip() or "0")
    except FileNotFoundError:
        i = 0
    p.write_text(str(i + 1))
    return i


class _Messages:
    def create(self, *, model: str, max_tokens: int, system: str,
               messages: list[dict[str, Any]], **_: Any) -> _Response:
        responses = _load_responses()
        i = _next_index()
        if i >= len(responses):
            raise RuntimeError(
                f"fake_anthropic: call {i} but fixture only has "
                f"{len(responses)} responses"
            )
        r = responses[i]
        return _Response(
            content=[_TextBlock(text=r["text"])],
            usage=_Usage(
                input_tokens=int(r["input_tokens"]),
                output_tokens=int(r["output_tokens"]),
            ),
            model=model,
        )


class Anthropic:
    def __init__(self, *, api_key: str | None = None, **_: Any) -> None:
        self.api_key = api_key
        self.messages = _Messages()
