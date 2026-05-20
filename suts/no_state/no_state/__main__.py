"""No-state reference SUT for retention-bench.

Reads JSONL events from stdin (per docs/sut-interface.md), responds on stdout.
Calls the Anthropic API with the question text *only* for QUIZ events.
Ignores DIR entirely. Floor row on the leaderboard.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Iterable

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
SYSTEM_PROMPT = (
    "You are a question-answering assistant for a retention benchmark. "
    "For each question you receive, emit your answer wrapped in "
    '<ANSWER id="..."> ... </ANSWER> tags, reusing the question id verbatim. '
    "Emit one ANSWER block per question, in order, with nothing else around "
    "them. If you do not know an answer, write Unknown inside the tags."
)

_QUESTION_RE = re.compile(
    r'<QUESTION\s+id="([^"]+)">(.*?)</QUESTION>', re.DOTALL
)


def _die(msg: str, code: int = 1) -> None:
    print(f"no-state SUT: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def _parse_questions(stage_input: str) -> list[tuple[str, str]]:
    return [(q, t.strip()) for q, t in _QUESTION_RE.findall(stage_input)]


def _user_prompt(questions: list[tuple[str, str]]) -> str:
    body = "\n".join(f'<QUESTION id="{q}">{t}</QUESTION>' for q, t in questions)
    return ('Answer each question. Wrap each answer as '
            '<ANSWER id="..."> ... </ANSWER>.\n\n' + body)


def _handle_event(client, model: str, event: dict) -> dict:
    eid = event["event_id"]
    etype = event["event_type"]
    if etype == "READ":
        return {"event_id": eid, "stage_output": ""}
    if etype == "QUIZ":
        questions = _parse_questions(event.get("stage_input", ""))
        if not questions:
            return {"event_id": eid, "stage_output": "",
                    "notes": "no <QUESTION> tags found in stage_input"}
        resp = client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _user_prompt(questions)}],
        )
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", None) == "text")
        usage = getattr(resp, "usage", None)
        return {
            "event_id": eid, "stage_output": text,
            "tokens_in": getattr(usage, "input_tokens", 0) if usage else 0,
            "tokens_out": getattr(usage, "output_tokens", 0) if usage else 0,
            "api_call_count": 1,
        }
    return {"event_id": eid, "stage_output": "",
            "notes": f"unknown event_type: {etype}"}


def _iter_events(stream: Iterable[str]):
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        _die("ANTHROPIC_API_KEY is not set; refusing to start.", code=2)

    try:
        import anthropic  # type: ignore
    except ImportError:
        _die("`anthropic` package is not installed (pip install anthropic).",
             code=2)

    model = os.environ.get("NO_STATE_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    for event in _iter_events(sys.stdin):
        response = _handle_event(client, model, event)
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
