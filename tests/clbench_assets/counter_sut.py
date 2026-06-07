#!/usr/bin/env python3
"""Counter SUT speaking retention_bench's SubprocessSystem contract.

One JSON request line in, one JSON reply line out. Persistent state lives in
``state.json`` in cwd — which the harness sets to the survive-dir. The count is
re-read from disk on *every* request, so a SIGKILL between requests is
transparent: the reply is identical whether or not the process was bounced, as
long as the survive-dir persisted. Wipe the survive-dir and the count restarts —
the stateless baseline.

Reports a token/FLOP self-report under ``resource`` so the SubprocessSystem's
``compute`` UsageEvent accounting has something to carry (mirrors how a real
constructive SUT reports ``flops``/``param_count``).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STATE = Path("state.json")  # cwd == survive-dir


def _load_count() -> int:
    if STATE.exists():
        return int(json.loads(STATE.read_text()).get("count", 0))
    return 0


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        _ = json.loads(line)  # request payload; content irrelevant for a counter
        count = _load_count() + 1
        STATE.write_text(json.dumps({"count": count}))
        reply = {
            "action": {"count": count},
            "resource": {
                "flops": 1000 * count,  # toy monotone compute signal
                "tokens_in": 5,
                "tokens_out": 1,
                "model_id": "counter-sut",
            },
        }
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
