#!/usr/bin/env python3
"""Trivial retention SUT for the C0 integration spike.

Speaks JSONL over stdin/stdout (one request line in, one reply line out).
Persistent state lives in ``state.json`` in the process cwd — which the harness
sets to the survive-dir (DIR). Each request increments a counter and reports it.

The point: a SIGKILL between requests loses *nothing*, because the counter is on
disk in the survive-dir. That is exactly the retention-across-hard-reset property
CL-Bench has no way to express today.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STATE = Path("state.json")  # cwd == DIR (the survive-dir)


def _load() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"count": 0}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        _ = json.loads(line)  # request payload; content irrelevant for the spike
        state = _load()
        state["count"] += 1
        STATE.write_text(json.dumps(state))
        sys.stdout.write(json.dumps({"count": state["count"]}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
