"""Trivial stub SUT for harness self-testing.

I/O contract per docs/sut-interface.md (M4 wire shape):
  - Reads one JSON object per line from stdin:
      {"event_id":..., "event_type":"READ|QUIZ", "stage_input":...}
  - Writes one JSON object per line to stdout:
      READ:  {"event_id":..., "stage_output":""}
      QUIZ:  {"event_id":..., "answers":[{"id":"q1","text":"STUB_ANSWER"}, ...]}
  - Exits on EOF.

Behaviour: emits a fixed STUB_ANSWER for every question. Does not call any model.
"""

from __future__ import annotations

import json
import re
import sys

_QUESTION_RE = re.compile(r'<QUESTION\s+id="([^"]+)">', re.DOTALL)
STUB_ANSWER = "STUB_ANSWER"


def _handle(event_id: str, event_type: str, stage_input: str) -> dict:
    if event_type == "READ":
        return {"event_id": event_id, "stage_output": ""}
    if event_type == "QUIZ":
        qids = _QUESTION_RE.findall(stage_input)
        return {
            "event_id": event_id,
            "answers": [{"id": qid, "text": STUB_ANSWER} for qid in qids],
        }
    return {"event_id": event_id, "stage_output": "",
            "notes": f"unknown event_type: {event_type!r}"}


def main() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        msg = json.loads(raw)
        event_id = msg["event_id"]
        event_type = msg.get("event_type", "")
        stage_input = msg.get("stage_input", "")
        reply = _handle(event_id, event_type, stage_input)
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
