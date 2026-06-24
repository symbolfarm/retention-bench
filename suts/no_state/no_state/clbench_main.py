"""CL-Bench entrypoint for the no-state (ephemeral) reference SUT — the retention floor.

This SUT answers the same ``symbolic_associative_retention`` TRAIN/RECALL/TRANSFER
protocol as ``associative_memory``, but keeps its memory **only in-process**: a
plain in-RAM dict that lives for the lifetime of the Python process and nothing
else. It deliberately has no ``_load_state``/``_save_state`` and never reads or
writes ``RETENTION_BENCH_DIR``.

Effect on the gain curve: within a single episode (``k=0``, no hard reset) recall
holds, because the in-RAM dict survives across requests in the same process. But
every hard RESET kills the process, and because nothing was persisted to the
survive-dir, the next process boots with an empty dict — so recall collapses to
the prior floor ``P`` for ``k>=1``. That *drop* from ``R(0)`` to ``P`` is the
point: it visually demonstrates that the hard RESET erases un-persisted working
state. See ``README.md`` for the rationale behind the ephemeral (rather than
truly-stateless) choice.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Iterable, Iterator

_OBJECT_RE = re.compile(r"^object:\s*(?P<object>\S+)\s*$", re.MULTILINE)
_ATTRIBUTE_RE = re.compile(r"^attribute:\s*(?P<attribute>\S+)\s*$", re.MULTILINE)
_BIN_RE = re.compile(r"^bin:\s*(?P<bin>\S+)\s*$", re.MULTILINE)


def _empty_state() -> dict[str, dict[str, str]]:
    return {"object_attributes": {}, "attribute_bins": {}}


def _match(pattern: re.Pattern[str], prompt: str) -> str | None:
    found = pattern.search(prompt)
    return found.group(1).strip().lower() if found else None


def _handle_query(state: dict[str, dict[str, str]], request: dict[str, Any]) -> dict[str, Any]:
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

    # No persistence: the in-RAM ``state`` is the only memory, and it dies with
    # the process. We never touch RETENTION_BENCH_DIR.
    resource = {
        "flops": 25 * (
            len(state["object_attributes"]) + len(state["attribute_bins"])
        ),
        "tokens_in": len(prompt) // 4,
        "tokens_out": 1,
        "model_id": "no-state",
    }
    return {"action": {"answer": answer}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    # In-RAM only: a fresh empty dict per process. There is no _load_state, so a
    # process started after a hard RESET begins with no memory of prior episodes.
    state = _empty_state()
    for request in _iter_requests(sys.stdin):
        reply = _handle_query(state, request)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
