"""CL-Bench entrypoint for the associative-memory reference SUT."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

STATE_FILENAME = "associations.json"

_OBJECT_RE = re.compile(r"^object:\s*(?P<object>\S+)\s*$", re.MULTILINE)
_ATTRIBUTE_RE = re.compile(r"^attribute:\s*(?P<attribute>\S+)\s*$", re.MULTILINE)
_BIN_RE = re.compile(r"^bin:\s*(?P<bin>\S+)\s*$", re.MULTILINE)


def _dir_path() -> Path:
    return Path(os.environ.get("RETENTION_BENCH_DIR", os.getcwd()))


def _empty_state() -> dict[str, dict[str, str]]:
    return {"object_attributes": {}, "attribute_bins": {}}


def _load_state(dir_path: Path) -> dict[str, dict[str, str]]:
    path = dir_path / STATE_FILENAME
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()
    state = _empty_state()
    for key in state:
        value = data.get(key)
        if isinstance(value, dict):
            state[key] = {str(k): str(v) for k, v in value.items()}
    return state


def _save_state(dir_path: Path, state: dict[str, dict[str, str]]) -> None:
    path = dir_path / STATE_FILENAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, sort_keys=True))
    os.replace(tmp, path)


def _match(pattern: re.Pattern[str], prompt: str) -> str | None:
    found = pattern.search(prompt)
    return found.group(1).strip().lower() if found else None


def _handle_query(state: dict[str, dict[str, str]], dir_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    prompt = str(request.get("prompt") or "")
    answer = "unknown"

    if prompt.startswith("TRAIN object_attribute"):
        obj = _match(_OBJECT_RE, prompt)
        attr = _match(_ATTRIBUTE_RE, prompt)
        if obj and attr:
            state["object_attributes"][obj] = attr
        answer = "stored"
    elif prompt.startswith("TRAIN attribute_bin_rule"):
        attr = _match(_ATTRIBUTE_RE, prompt)
        bin_name = _match(_BIN_RE, prompt)
        if attr and bin_name:
            state["attribute_bins"][attr] = bin_name
        answer = "stored"
    elif prompt.startswith("RECALL object_attribute"):
        obj = _match(_OBJECT_RE, prompt)
        answer = state["object_attributes"].get(obj or "", "unknown")
    elif prompt.startswith("TRANSFER object_bin"):
        obj = _match(_OBJECT_RE, prompt)
        attr = state["object_attributes"].get(obj or "")
        answer = state["attribute_bins"].get(attr or "", "unknown")

    _save_state(dir_path, state)
    resource = {
        "flops": 25 * (
            len(state["object_attributes"]) + len(state["attribute_bins"])
        ),
        "tokens_in": len(prompt) // 4,
        "tokens_out": 1,
        "model_id": "associative-memory",
    }
    return {"action": {"answer": answer}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    dir_path = _dir_path()
    state = _load_state(dir_path)
    for request in _iter_requests(sys.stdin):
        reply = _handle_query(state, dir_path, request)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
