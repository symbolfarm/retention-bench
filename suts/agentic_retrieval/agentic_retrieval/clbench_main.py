"""Iterative-retrieval LLM SUT for the widened associative task.

TRAIN facts are appended to the survive-dir. RECALL does one disk lookup;
TRANSFER does two dependent disk lookups (object -> attribute, then attribute ->
bin) before one pinned LLM call formats the answer. Every lookup and raw model
reply is copied to the reserved trace area for durable measurement evidence.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
FACTS_FILE = "facts.jsonl"
TRACE_FILE = "agentic-trace.jsonl"
_FIELD = re.compile(r"^(object|attribute|bin|role):\s*(\S+)\s*$", re.MULTILINE)


def _fields(prompt: str) -> dict[str, str]:
    return dict(_FIELD.findall(prompt))


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _store_training_fact(path: Path, prompt: str) -> dict[str, Any]:
    fields = _fields(prompt)
    if prompt.startswith("TRAIN object_attribute"):
        row = {"kind": "object_attribute", "object": fields["object"],
               "attribute": fields["attribute"], "role": fields.get("role")}
    elif prompt.startswith("TRAIN attribute_bin_rule"):
        row = {"kind": "attribute_bin", "attribute": fields["attribute"],
               "bin": fields["bin"]}
    else:
        raise ValueError(f"unsupported TRAIN prompt: {prompt!r}")
    _append_jsonl(path, row)
    return row


def lookup(path: Path, field: str, value: str) -> list[dict[str, Any]]:
    """Perform one observable retrieval by reading the survive-dir store."""
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [row for row in rows if row.get(field) == value]


def retrieve(path: Path, prompt: str) -> list[dict[str, Any]]:
    """Return the query-dependent lookup chain, including each query and hits."""
    fields = _fields(prompt)
    obj = fields.get("object", "")
    first = lookup(path, "object", obj)
    chain: list[dict[str, Any]] = [{"query": f"object:{obj}", "hits": first}]
    if prompt.startswith("TRANSFER"):
        attribute = first[-1].get("attribute", "") if first else ""
        second = lookup(path, "attribute", str(attribute))
        second = [row for row in second if row.get("kind") == "attribute_bin"]
        chain.append({"query": f"attribute:{attribute}", "hits": second})
    return chain


def _usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    extra = getattr(usage, "model_extra", None) or {}
    cost = extra.get("cost")
    return {
        "tokens_in": int(getattr(usage, "prompt_tokens", 0) or 0),
        "tokens_out": int(getattr(usage, "completion_tokens", 0) or 0),
        "cost_usd": float(cost) if cost is not None else None,
    }


def _answer(client: Any, model: str, prompt: str, chain: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any], str | None]:
    context = json.dumps(chain, ensure_ascii=False)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        # This model emits hidden reasoning tokens that count against the
        # completion budget. 32 produced mostly empty/truncated replies in the
        # first pilot; 256 leaves room for reasoning plus the tiny JSON answer.
        max_completion_tokens=256,
        messages=[
            {"role": "system", "content": "Answer using only RETRIEVAL_CHAIN. Return one JSON object with exactly one string field named answer. No prose."},
            {"role": "user", "content": f"QUERY:\n{prompt}\n\nRETRIEVAL_CHAIN:\n{context}"},
        ],
    )
    raw = response.choices[0].message.content or ""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        return "", raw, _usage(response), "no JSON object"
    try:
        parsed = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        return "", raw, _usage(response), f"invalid JSON: {exc.msg}"
    answer = parsed.get("answer") if isinstance(parsed, dict) else None
    if not isinstance(answer, str):
        return "", raw, _usage(response), "answer is not a string"
    return answer, raw, _usage(response), None


def handle(request: dict[str, Any], client: Any, model: str, store: Path, trace: Path) -> dict[str, Any]:
    prompt = str(request.get("prompt") or "")
    instance_id = request.get("instance_id")
    if prompt.startswith("TRAIN"):
        fact = _store_training_fact(store, prompt)
        row = {"instance_id": instance_id, "kind": "train", "stored": fact,
               "retrieval_count": 0, "lookups": [], "raw_model_reply": None,
               "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        _append_jsonl(trace, row)
        return {"action": {"answer": "stored"}, "resource": {
            "model_id": model, "api_call_count": 0, "retrieval_count": 0,
            "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}}

    chain = retrieve(store, prompt)
    answer, raw, usage, parse_error = _answer(client, model, prompt, chain)
    row = {"instance_id": instance_id, "kind": "query", "prompt": prompt,
           "retrieval_count": len(chain), "lookups": chain,
           "raw_model_reply": raw, "parse_error": parse_error, **usage}
    _append_jsonl(trace, row)
    return {"action": {"answer": answer}, "resource": {
        "model_id": model, "api_call_count": 1,
        "retrieval_count": len(chain), **usage}}


def _requests(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in lines:
        if line.strip():
            yield json.loads(line)


def main() -> None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set; refusing to start")
    import openai
    model = os.environ.get("AGENTIC_RETRIEVAL_MODEL", DEFAULT_MODEL)
    if model != DEFAULT_MODEL:
        raise SystemExit(f"RB-19 requires exact model {DEFAULT_MODEL!r}, got {model!r}")
    client = openai.OpenAI(api_key=key, base_url=os.environ.get("RETENTION_BENCH_BASE_URL", DEFAULT_BASE_URL))
    cwd = Path.cwd()
    store = cwd / FACTS_FILE
    trace = cwd / ".harness" / TRACE_FILE
    for request in _requests(sys.stdin):
        reply = handle(request, client, model, store, trace)
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
