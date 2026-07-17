"""CL-Bench entrypoint for the reset-lossy reference SUT.

Mirrors ``associative_memory`` (full survive-dir persistence of trained facts)
but loses a deterministic fraction of its retained state *on each hard reset* —
the **graded** rung of the reference ladder. Unlike ``bounded_memory`` (whose
FIFO cap lowers the *ceiling* but lets everything it holds survive every reset
intact), this SUT keeps every fact it was taught on disk yet *answers* fewer and
fewer of them as the number of resets survived grows. So its normalised
retention lands strictly between 0 and 1, and it is the first reference SUT where
the reset *count* matters: ``R(every_1)`` (more resets) sits below
``R(every_2)``.

### Deterministic decay mechanism

The survive-dir holds two things:

  * ``reset_lossy.json`` — the full set of trained facts (never pruned), and
  * a ``load_count`` — incremented (and persisted) once per process start.

A fresh run starts the process once (``load_count == 1``); each hard reset
SIGKILLs the process and the runner respawns it, bumping ``load_count`` again.
So ``k = load_count - 1`` is exactly the number of resets the on-disk state has
survived at the moment this process answers a probe.

Each fact is assigned a stable pseudo-uniform value ``u(fact) in [0, 1)`` via a
fixed BLAKE2b hash of its identity (no per-run randomness, no seed file). A fact
is *answered* only while ``u(fact) < (1 - rate) ** k``. This is textbook
**geometric (exponential) forgetting**: a constant fraction ``rate`` of the
still-recalled facts is dropped on each hard reset, so the answered fraction is
``(1 - rate) ** k`` after ``k`` resets — monotone-decreasing in ``k``, fully
deterministic, and (unlike a capacity cap) reset-*count*-sensitive. Facts are
never deleted from disk — only the answer gate moves — which keeps the mechanism
cleanly distinct from ``bounded_memory``'s capacity eviction. Because retention
is a genuine exponential in ``k``, ``R(k)`` traces a real decay curve.

``rate`` is the per-reset loss fraction. The default is deliberately *small*
(``DEFAULT_RATE``) because this task drives 12-25 hard resets before its probes
run: a large per-reset rate compounds to a total wipe-out over that many resets
(e.g. ``0.7 ** 12 ≈ 0.014``), collapsing the rung onto the floor. A small rate
lands the curve in the graded band (``0 < norm < 1``) while keeping the
interpretation honest — "loses a few percent of recallable facts per reset".

Loss rate defaults to ``DEFAULT_RATE`` and is overridable via the
``RESET_LOSSY_RATE`` environment variable (a float in ``[0, 1)``; out-of-range
or non-numeric values raise ``ValueError`` rather than silently falling back —
for a benchmark, a typo'd experiment parameter running the default unnoticed is
worse than a crash).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

STATE_FILENAME = "reset_lossy.json"
DEFAULT_RATE = 0.05

_OBJECT_RE = re.compile(r"^object:\s*(?P<object>\S+)\s*$", re.MULTILINE)
_ATTRIBUTE_RE = re.compile(r"^attribute:\s*(?P<attribute>\S+)\s*$", re.MULTILINE)
_BIN_RE = re.compile(r"^bin:\s*(?P<bin>\S+)\s*$", re.MULTILINE)


def _dir_path() -> Path:
    return Path(os.environ.get("RETENTION_BENCH_DIR", os.getcwd()))


def _rate() -> float:
    raw = os.environ.get("RESET_LOSSY_RATE")
    if raw is None:
        return DEFAULT_RATE
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"RESET_LOSSY_RATE must be a float, got {raw!r}"
        ) from exc
    if not (0.0 <= value < 1.0):
        raise ValueError(
            f"RESET_LOSSY_RATE must be in [0.0, 1.0), got {value!r}"
        )
    return value


def _empty_state() -> dict[str, Any]:
    return {"object_attributes": {}, "attribute_bins": {}, "load_count": 0}


def _load_state(dir_path: Path) -> dict[str, Any]:
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
    for key in ("object_attributes", "attribute_bins"):
        value = data.get(key)
        if isinstance(value, dict):
            state[key] = {str(k): str(v) for k, v in value.items()}
    raw_load = data.get("load_count")
    state["load_count"] = raw_load if isinstance(raw_load, int) and raw_load >= 0 else 0
    return state


def _save_state(dir_path: Path, state: dict[str, Any]) -> None:
    path = dir_path / STATE_FILENAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, sort_keys=True))
    os.replace(tmp, path)


def _u(kind: str, key: str) -> float:
    """Stable pseudo-uniform value in [0, 1) for a fact identity (fixed hash)."""
    digest = hashlib.blake2b(f"{kind}\x00{key}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2 ** 64


def _survives(kind: str, key: str, resets: int, rate: float) -> bool:
    """True iff the fact is still answered after ``resets`` hard resets.

    Geometric forgetting: a fact survives while ``u(fact) < (1 - rate) ** resets``,
    so the answered fraction decays as a constant ``rate`` per reset (see module
    docstring). Monotone-decreasing in ``resets``, fully deterministic.
    """
    threshold = (1.0 - rate) ** resets
    return _u(kind, key) < threshold


def _match(pattern: re.Pattern[str], prompt: str) -> str | None:
    found = pattern.search(prompt)
    return found.group(1).strip().lower() if found else None


def _handle_query(
    state: dict[str, Any], dir_path: Path, resets: int, rate: float, request: dict[str, Any]
) -> dict[str, Any]:
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
        obj = _match(_OBJECT_RE, prompt) or ""
        if obj in state["object_attributes"] and _survives("object_attribute", obj, resets, rate):
            answer = state["object_attributes"][obj]
    elif prompt.startswith("TRANSFER object_bin"):
        obj = _match(_OBJECT_RE, prompt) or ""
        # The chain survives only if the object->attribute fact survives; the
        # attribute->bin rule is then looked up (gated on its own survival).
        if obj in state["object_attributes"] and _survives("object_attribute", obj, resets, rate):
            attr = state["object_attributes"][obj]
            if attr in state["attribute_bins"] and _survives("attribute_bin", attr, resets, rate):
                answer = state["attribute_bins"][attr]

    _save_state(dir_path, state)
    resource = {
        "flops": 25 * (
            len(state["object_attributes"]) + len(state["attribute_bins"])
        ),
        "tokens_in": len(prompt) // 4,
        "tokens_out": 1,
        "model_id": "reset-lossy",
    }
    return {"action": {"answer": answer}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    dir_path = _dir_path()
    rate = _rate()
    state = _load_state(dir_path)
    # Bump and persist the load counter once per process start, so it tracks the
    # number of (re)spawns; resets survived is one less than the load count.
    state["load_count"] = int(state["load_count"]) + 1
    resets = state["load_count"] - 1
    _save_state(dir_path, state)
    for request in _iter_requests(sys.stdin):
        reply = _handle_query(state, dir_path, resets, rate, request)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
