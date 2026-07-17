"""CL-Bench entrypoint for the bounded-memory reference SUT.

Mirrors ``associative_memory`` but persists only a capped FIFO window of the most
recently trained facts. Facts pushed out of the window by newer facts are
evicted and fail recall/transfer, so retention is *partial*: the gain curve sits
between the no-state floor and a full retainer.

The cap defaults to ``DEFAULT_CAP`` entries and is overridable via the
``BOUNDED_MEMORY_CAP`` environment variable (a positive int; invalid or
out-of-range values raise ``ValueError`` rather than silently falling back).
The FIFO is global across both fact kinds (object->attribute facts and
attribute->bin rules): every stored fact counts against the same window,
ordered by insertion / most-recent overwrite.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

STATE_FILENAME = "bounded_associations.json"
DEFAULT_CAP = 8

_OBJECT_RE = re.compile(r"^object:\s*(?P<object>\S+)\s*$", re.MULTILINE)
_ATTRIBUTE_RE = re.compile(r"^attribute:\s*(?P<attribute>\S+)\s*$", re.MULTILINE)
_BIN_RE = re.compile(r"^bin:\s*(?P<bin>\S+)\s*$", re.MULTILINE)


def _dir_path() -> Path:
    return Path(os.environ.get("RETENTION_BENCH_DIR", os.getcwd()))


def _cap() -> int:
    raw = os.environ.get("BOUNDED_MEMORY_CAP")
    if raw is None:
        return DEFAULT_CAP
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"BOUNDED_MEMORY_CAP must be an int, got {raw!r}"
        ) from exc
    if value < 1:
        raise ValueError(f"BOUNDED_MEMORY_CAP must be >= 1, got {value!r}")
    return value


# State is an ordered list of fact entries, oldest first. Each entry is a dict:
#   {"kind": "object_attribute"|"attribute_bin", "key": str, "value": str}
# The list order is the FIFO order used for eviction.
State = list[dict[str, str]]


def _empty_state() -> State:
    return []


def _load_state(dir_path: Path) -> State:
    path = dir_path / STATE_FILENAME
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _empty_state()
    if not isinstance(data, list):
        return _empty_state()
    state: State = []
    for item in data:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        key = item.get("key")
        value = item.get("value")
        if kind in ("object_attribute", "attribute_bin") and key is not None and value is not None:
            state.append({"kind": str(kind), "key": str(key), "value": str(value)})
    return state


def _save_state(dir_path: Path, state: State) -> None:
    path = dir_path / STATE_FILENAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, path)


def _store(state: State, kind: str, key: str, value: str, cap: int) -> None:
    """Insert/refresh a fact at the most-recent end, then evict to the cap (FIFO)."""
    for i, entry in enumerate(state):
        if entry["kind"] == kind and entry["key"] == key:
            del state[i]
            break
    state.append({"kind": kind, "key": key, "value": value})
    while len(state) > cap:
        del state[0]


def _lookup(state: State, kind: str, key: str | None) -> str | None:
    if key is None:
        return None
    for entry in state:
        if entry["kind"] == kind and entry["key"] == key:
            return entry["value"]
    return None


def _match(pattern: re.Pattern[str], prompt: str) -> str | None:
    found = pattern.search(prompt)
    return found.group(1).strip().lower() if found else None


def _handle_query(state: State, dir_path: Path, cap: int, request: dict[str, Any]) -> dict[str, Any]:
    prompt = str(request.get("prompt") or "")
    answer = "unknown"

    if prompt.startswith("TRAIN object_attribute"):
        obj = _match(_OBJECT_RE, prompt)
        attr = _match(_ATTRIBUTE_RE, prompt)
        if obj and attr:
            _store(state, "object_attribute", obj, attr, cap)
        answer = "stored"
    elif prompt.startswith("TRAIN attribute_bin_rule"):
        attr = _match(_ATTRIBUTE_RE, prompt)
        bin_name = _match(_BIN_RE, prompt)
        if attr and bin_name:
            _store(state, "attribute_bin", attr, bin_name, cap)
        answer = "stored"
    elif prompt.startswith("RECALL object_attribute"):
        obj = _match(_OBJECT_RE, prompt)
        answer = _lookup(state, "object_attribute", obj) or "unknown"
    elif prompt.startswith("TRANSFER object_bin"):
        obj = _match(_OBJECT_RE, prompt)
        attr = _lookup(state, "object_attribute", obj)
        answer = _lookup(state, "attribute_bin", attr) or "unknown"

    _save_state(dir_path, state)
    resource = {
        "flops": 25 * len(state),
        "tokens_in": len(prompt) // 4,
        "tokens_out": 1,
        "model_id": "bounded-memory",
    }
    return {"action": {"answer": answer}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    dir_path = _dir_path()
    cap = _cap()
    state = _load_state(dir_path)
    for request in _iter_requests(sys.stdin):
        reply = _handle_query(state, dir_path, cap, request)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
