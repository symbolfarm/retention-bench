"""Notes-LLM SUT — Continual Learning Bench entrypoint (C11).

The book-track entrypoint (``notes_llm.__main__``) speaks the READ/QUIZ event
contract. This one speaks the **Continual Learning Bench** wire contract driven
by ``retention_bench.SubprocessSystem`` (C2):

    request : {"prompt": str, "instance_id": str|null, "instance_index": int|null,
               "response_schema": {<JSON Schema>}, "feedback": str|null}
    reply   : {"action": {<fields matching response_schema>},
               "resource": {"tokens_in": int, "tokens_out": int, "model_id": str,
                            "api_call_count": int}}

This is the **in-context validation SUT** (C11): the first retention-bench SUT
meant to *lift the curve above the stateless prior*, proving the gain-vs-`k`
machinery measures a real curve. It is sourced from a capable API model — it is
NOT the constructive research model (that lives in its own project; see
``docs/constructive-sut-development-brief.md``).

CL-Bench single-shot tasks have no separate READ stage: each *query* is both a
new observation and a request for a structured report. So per query the SUT:

  1. **updates its notes** — one LLM call revises ``DIR/notes.md`` to capture the
     persistent/latent structure across all observations seen so far (the
     observation is the query ``prompt``); the notes are the retained artifact;
  2. **answers from the notes** — a second LLM call emits a JSON object
     conforming to the query's ``response_schema``, derived only from the notes
     (the model never sees past prompts directly — only what it chose to keep).

Retention mechanism: notes accumulate structure a single observation can't
reveal (e.g. which spectrum regions are *persistently* occupied vs. merely
active on one scan). A hard RESET wipes the notes → back to the single-observation
prior. The notes are **flushed to DIR before the reply**, so they survive the
SIGKILL; a fresh process reloads them on spawn.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

# Reuse the book-track SUT's note I/O + LLM-call helpers — same model, same
# atomic-notes discipline, so the two entrypoints stay one codebase.
from notes_llm.__main__ import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    NOTES_FILENAME,
    _call_llm,
    _die,
    _extract_notes,
    _read_notes,
    _write_notes_atomic,
)

NOTES_BUDGET_TOKENS = 2000

NOTES_SYSTEM_PROMPT = (
    "You are keeping cumulative notes across a stream of observations for a "
    "retention benchmark. You will be shown your existing notes (possibly "
    "empty) and ONE new observation. Produce a revised, cumulative notes file "
    "that captures the PERSISTENT, recurring, or latent structure across all "
    "observations seen so far — not just the surface of this single one. You "
    "will later answer using only these notes; you will NOT see past "
    "observations again.\n\n"
    "Prefer durable structure (what recurs, what is stable, what the underlying "
    "system looks like) over one-off details. Decide what to keep, revise, or "
    f"drop. Aim for under ~{NOTES_BUDGET_TOKENS} tokens; shorter is better if "
    "recall is preserved.\n\n"
    "Wrap the full revised notes inside <NOTES> ... </NOTES> tags. Emit nothing "
    "outside those tags."
)

REPORT_SYSTEM_PROMPT = (
    "You are producing a structured report for a retention benchmark, using "
    "ONLY your accumulated notes (you no longer have access to the raw "
    "observations). Reason about the persistent/long-run structure your notes "
    "describe.\n\n"
    "Reply with a SINGLE JSON object that conforms to the provided JSON Schema "
    "— no prose, no markdown fences, just the JSON object."
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _notes_user_prompt(prior_notes: str, observation: str) -> str:
    prior = prior_notes.strip() or "(no prior notes yet — this is the first observation)"
    return (
        "Your existing notes:\n<PRIOR_NOTES>\n"
        f"{prior}\n</PRIOR_NOTES>\n\n"
        "New observation:\n<OBSERVATION>\n"
        f"{observation}\n</OBSERVATION>\n\n"
        "Produce the revised cumulative notes file, wrapped in <NOTES> tags."
    )


def _report_user_prompt(notes: str, response_schema: dict[str, Any]) -> str:
    notes_block = notes.strip() or "(notes file is empty)"
    return (
        "Your accumulated notes:\n<NOTES>\n"
        f"{notes_block}\n</NOTES>\n\n"
        "JSON Schema your reply MUST conform to:\n"
        f"{json.dumps(response_schema, ensure_ascii=False)}\n\n"
        "Reply with a single conforming JSON object and nothing else."
    )


# --------------------------------------------------------------------------- #
# Structured-output parsing + a minimal-valid fallback (so the runner — which
# does response_schema(**action) — never crashes on a malformed reply).
# --------------------------------------------------------------------------- #
def _extract_json(text: str) -> Optional[dict[str, Any]]:
    stripped = _FENCE_RE.sub("", text).strip()
    # Be lenient: find the outermost {...} if the model wrapped it in prose.
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        obj = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _resolve_ref(ref: str, defs: dict[str, Any]) -> dict[str, Any]:
    prefix = "#/$defs/"
    return defs.get(ref[len(prefix) :], {}) if ref.startswith(prefix) else {}


def _minimal_valid(schema: dict[str, Any], defs: dict[str, Any]) -> Any:
    """Smallest value satisfying ``schema`` — the fallback when the model's JSON
    is unusable. Required object fields get type-appropriate empties; arrays get
    ``[]`` (or ``minItems`` empties); scalars get zero/empty values."""
    if "$ref" in schema:
        return _minimal_valid(_resolve_ref(schema["$ref"], defs), defs)
    typ = schema.get("type")
    if isinstance(typ, list):  # e.g. ["string", "null"] — pick the first concrete
        typ = next((t for t in typ if t != "null"), typ[0] if typ else None)
    if typ == "object":
        props = schema.get("properties", {})
        required = schema.get("required", [])
        return {k: _minimal_valid(props[k], defs) for k in required if k in props}
    if typ == "array":
        item = schema.get("items", {})
        return [_minimal_valid(item, defs) for _ in range(int(schema.get("minItems", 0)))]
    if typ == "number":
        return 0.0
    if typ == "integer":
        return 0
    if typ == "boolean":
        return False
    return ""  # string / unknown


def _coerce_action(parsed: Optional[dict[str, Any]], response_schema: dict[str, Any]) -> dict[str, Any]:
    """Return a dict to spread into ``response_schema(**action)``. Use the model
    output if it carries the required top-level keys; otherwise fall back to a
    minimal valid object so the run never crashes on a bad reply."""
    defs = response_schema.get("$defs", {})
    required = response_schema.get("required", [])
    if isinstance(parsed, dict) and all(k in parsed for k in required):
        return parsed
    fallback = _minimal_valid(response_schema, defs)
    if not isinstance(fallback, dict):
        fallback = {}
    # Keep any usable keys the model did supply, on top of the valid skeleton.
    if isinstance(parsed, dict):
        fallback.update({k: v for k, v in parsed.items() if k in response_schema.get("properties", {})})
    return fallback


# --------------------------------------------------------------------------- #
# Per-query handling.
# --------------------------------------------------------------------------- #
def _handle_query(client, model: str, notes_path: Path, request: dict) -> dict:
    observation = request.get("prompt", "") or ""
    response_schema = request.get("response_schema") or {"type": "object", "properties": {}}

    # 1. Update notes from this observation, FLUSH before replying (survives RESET).
    prior = _read_notes(notes_path)
    notes_text, tin1, tout1 = _call_llm(
        client, model, NOTES_SYSTEM_PROMPT, _notes_user_prompt(prior, observation)
    )
    new_notes = _extract_notes(notes_text)
    _write_notes_atomic(notes_path, new_notes)

    # 2. Produce the structured report from the notes alone.
    report_text, tin2, tout2 = _call_llm(
        client, model, REPORT_SYSTEM_PROMPT, _report_user_prompt(new_notes, response_schema)
    )
    action = _coerce_action(_extract_json(report_text), response_schema)

    return {
        "action": action,
        "resource": {
            "tokens_in": tin1 + tin2,
            "tokens_out": tout1 + tout2,
            "model_id": model,
            "api_call_count": 2,
        },
    }


def _iter_requests(stream: Iterable[str]) -> Iterator[dict]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _die("OPENROUTER_API_KEY is not set; refusing to start.", code=2)
    try:
        import openai  # type: ignore
    except ImportError:
        _die("`openai` package is not installed (pip install openai).", code=2)

    model = os.environ.get("NOTES_LLM_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("RETENTION_BENCH_BASE_URL", DEFAULT_BASE_URL)
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    notes_path = Path.cwd() / NOTES_FILENAME

    for request in _iter_requests(sys.stdin):
        reply = _handle_query(client, model, notes_path, request)
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
