"""Trivial stub SUT for harness self-testing.

I/O contract (matches M2 pre-locked decision):
  - Reads one JSON object per line from stdin:
      {"event_id":..., "event_type":"READ|QUIZ", "stage_input":...}
  - Writes one JSON object per line to stdout:
      {"event_id":..., "stage_output":...}
  - Exits on EOF.

Behaviour:
  - READ: returns empty stage_output ("").
  - QUIZ: parses <QUESTION id="..."> tags from stage_input and emits a
    fixed-string <ANSWER id="..."> for each. Does NOT attempt to answer.
"""

from __future__ import annotations

import json
import re
import sys

_QUESTION_RE = re.compile(r'<QUESTION\s+id="([^"]+)">', re.DOTALL)
STUB_ANSWER = "STUB_ANSWER"


def _handle(event_id: str, event_type: str, stage_input: str) -> str:
    if event_type == "READ":
        return ""
    if event_type == "QUIZ":
        qids = _QUESTION_RE.findall(stage_input)
        return "\n".join(f'<ANSWER id="{qid}">{STUB_ANSWER}</ANSWER>' for qid in qids)
    return ""


def main() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        msg = json.loads(raw)
        event_id = msg["event_id"]
        event_type = msg.get("event_type", "")
        stage_input = msg.get("stage_input", "")
        stage_output = _handle(event_id, event_type, stage_input)
        sys.stdout.write(json.dumps({"event_id": event_id, "stage_output": stage_output}) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
