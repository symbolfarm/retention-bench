"""Fake `openai` SDK shim for retention-bench integration tests.

Shadows the real `openai` package when its parent directory is prepended
to PYTHONPATH: a top-level ``openai.py`` module wins over the installed
``openai/`` package regardless of sys.path order between a module and a
package of the same name (first on the path wins). Returns canned
responses keyed by call sequence, loaded from a YAML fixture pointed to
by env var.

Env contract:
  FAKE_OPENAI_FIXTURE  Path to a YAML file with a `responses` list, each
                       entry having either:
                         - `text`, `input_tokens`, `output_tokens`
                           (text response)
                         - `tool_use`, `input_tokens`, `output_tokens`
                           where `tool_use` has `name` and `input` keys
                           (function-call response — for judge scorer tests)
                       The fixture format is provider-neutral and unchanged
                       from the old fake-anthropic shim. This shim maps it
                       onto OpenAI response shape: the tool `input` dict is
                       JSON-encoded into the function-call `arguments` string,
                       and `input_tokens`/`output_tokens` become
                       `prompt_tokens`/`completion_tokens` on `usage`.
  FAKE_OPENAI_COUNTER  Path to a file storing the next call index as ASCII
                       int. Shared across SUT subprocesses within a single
                       test run; lets us prove that respawned SUTs (after
                       RESET) successfully imported this shim and continued
                       the sequence.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class _Function:
    name: str
    arguments: str  # JSON-encoded string, matching the real OpenAI SDK


@dataclass
class _ToolCall:
    function: _Function
    id: str = "fake-tool-call-id"
    type: str = "function"


@dataclass
class _Message:
    content: str | None
    tool_calls: list | None = None
    role: str = "assistant"


@dataclass
class _Choice:
    message: _Message
    index: int = 0
    finish_reason: str = "stop"


@dataclass
class _Usage:
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class _Response:
    choices: list
    usage: _Usage
    model: str


def _load_responses() -> list[dict[str, Any]]:
    path = os.environ.get("FAKE_OPENAI_FIXTURE")
    if not path:
        raise RuntimeError("FAKE_OPENAI_FIXTURE env var is not set")
    data = yaml.safe_load(Path(path).read_text())
    return data["responses"]


def _next_index() -> int:
    path = os.environ.get("FAKE_OPENAI_COUNTER")
    if not path:
        raise RuntimeError("FAKE_OPENAI_COUNTER env var is not set")
    p = Path(path)
    try:
        i = int(p.read_text().strip() or "0")
    except FileNotFoundError:
        i = 0
    p.write_text(str(i + 1))
    return i


class _Completions:
    def create(self, *, model: str, messages: list[dict[str, Any]],
               **_: Any) -> _Response:
        responses = _load_responses()
        i = _next_index()
        if i >= len(responses):
            raise RuntimeError(
                f"fake_openai: call {i} but fixture only has "
                f"{len(responses)} responses"
            )
        r = responses[i]
        usage = _Usage(
            prompt_tokens=int(r["input_tokens"]),
            completion_tokens=int(r["output_tokens"]),
        )
        if "tool_use" in r:
            tu = r["tool_use"]
            # The real OpenAI SDK returns function-call arguments as a JSON
            # *string*; callers json.loads() it. (Anthropic returned an
            # already-parsed dict on a tool_use block — that shape difference
            # is the whole reason scorer/judge.py json.loads the arguments.)
            tool_call = _ToolCall(
                function=_Function(
                    name=tu["name"],
                    arguments=json.dumps(tu["input"]),
                )
            )
            message = _Message(content=None, tool_calls=[tool_call])
        else:
            message = _Message(content=r["text"], tool_calls=None)
        return _Response(
            choices=[_Choice(message=message)],
            usage=usage,
            model=model,
        )


class _Chat:
    def __init__(self) -> None:
        self.completions = _Completions()


class OpenAI:
    def __init__(self, *, api_key: str | None = None,
                 base_url: str | None = None, **_: Any) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.chat = _Chat()
