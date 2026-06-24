"""Notes-LLM reference SUT for retention-bench.

Reads JSONL events from stdin (per docs/sut-interface.md), responds on stdout.
On READ: takes cumulative freeform notes to DIR/notes.md via one LLM call.
On QUIZ: answers from DIR/notes.md via one LLM call.

Cumulative notes: every READ shows the model its prior notes file plus the
new chapter, and asks for a revised full notes file. The model picks the
format (bullets, prose, Q&A) and chooses what to keep, revise, drop.

Same model used for READ and QUIZ so the retention curve isolates the value
of notes rather than a model swap.

Wire contract: QUIZ replies carry a structured `answers` list of
{"id": <qid>, "text": <answer>}. The model is asked to emit <ANSWER>-tagged
output; that's our internal convention for extracting per-question answers.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 4096
NOTES_FILENAME = "notes.md"
NOTES_BUDGET_TOKENS = 2000  # advisory only, surfaced in the system prompt

READ_SYSTEM_PROMPT = (
    "You are taking study notes for a retention benchmark. You will be shown "
    "your existing notes (possibly empty) followed by a new chapter of source "
    "material. Produce a revised, cumulative notes file that you will later "
    "use to answer questions about ALL chapters seen so far — you will not "
    "have access to the chapter text at quiz time, only these notes.\n\n"
    "Choose your own format (bullets, prose, Q&A). Decide what to keep, "
    f"revise, or drop. Aim for under ~{NOTES_BUDGET_TOKENS} tokens of notes; "
    "there is no hard cap but shorter is better if you can preserve recall.\n\n"
    "Wrap the full revised notes file inside <NOTES> ... </NOTES> tags. Emit "
    "nothing outside those tags."
)

QUIZ_SYSTEM_PROMPT = (
    "You are a question-answering assistant for a retention benchmark. You "
    "will be shown your study notes (which you wrote earlier from source "
    "material you no longer have access to), followed by questions. Answer "
    "each question using only the notes.\n\n"
    "For each question, emit your answer wrapped in "
    '<ANSWER id="..."> ... </ANSWER> tags, reusing the question id verbatim. '
    "Emit one ANSWER block per question, in order, with nothing else around "
    "them. If the notes do not contain the answer, write Unknown inside the "
    "tags."
)

_QUESTION_RE = re.compile(
    r'<QUESTION\s+id="([^"]+)">(.*?)</QUESTION>', re.DOTALL
)
_ANSWER_RE = re.compile(
    r'<ANSWER\s+id="([^"]+)">(.*?)</ANSWER>', re.DOTALL
)
_NOTES_RE = re.compile(r"<NOTES>(.*?)</NOTES>", re.DOTALL)
_TEXT_RE = re.compile(r"<TEXT>\s*(.*?)\s*</TEXT>", re.DOTALL)


def _die(msg: str, code: int = 1) -> None:
    print(f"notes-llm SUT: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def _parse_chapter(stage_input: str) -> str:
    m = _TEXT_RE.search(stage_input)
    return m.group(1) if m else ""


def _parse_questions(stage_input: str) -> list[tuple[str, str]]:
    return [(q, t.strip()) for q, t in _QUESTION_RE.findall(stage_input)]


def _read_notes(notes_path: Path) -> str:
    try:
        return notes_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _write_notes_atomic(notes_path: Path, content: str) -> None:
    tmp = notes_path.with_suffix(notes_path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, notes_path)


def _read_user_prompt(prior_notes: str, chapter_text: str) -> str:
    prior = prior_notes.strip() or "(no prior notes yet — this is the first chapter)"
    return (
        "Your existing notes:\n"
        "<PRIOR_NOTES>\n"
        f"{prior}\n"
        "</PRIOR_NOTES>\n\n"
        "New chapter:\n"
        "<CHAPTER>\n"
        f"{chapter_text}\n"
        "</CHAPTER>\n\n"
        "Produce the revised cumulative notes file, wrapped in <NOTES> tags."
    )


def _quiz_user_prompt(notes: str, questions: list[tuple[str, str]]) -> str:
    notes_block = notes.strip() or "(notes file is empty)"
    body = "\n".join(f'<QUESTION id="{q}">{t}</QUESTION>' for q, t in questions)
    return (
        "Your study notes:\n"
        "<NOTES>\n"
        f"{notes_block}\n"
        "</NOTES>\n\n"
        "Questions:\n"
        f"{body}\n\n"
        'Answer each question. Wrap each answer as <ANSWER id="..."> ... </ANSWER>.'
    )


def _extract_notes(model_text: str) -> str:
    """Parse <NOTES>...</NOTES> from the model's response.

    Fallback: if the model forgot tags, treat the whole reply as notes —
    losing the file would lose all retention signal, which is worse than
    carrying a sloppy reply.
    """
    m = _NOTES_RE.search(model_text)
    return m.group(1).strip() if m else model_text.strip()


def _extract_answers(model_text: str) -> list[dict]:
    out: list[dict] = []
    for m in _ANSWER_RE.finditer(model_text):
        qid, body = m.group(1), m.group(2).strip()
        out.append({"id": qid, "text": body})
    return out


def _call_llm(client, model: str, system: str, user: str):
    resp = client.chat.completions.create(
        model=model, max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
    tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
    return text, tokens_in, tokens_out


def _handle_event(client, model: str, notes_path: Path, event: dict) -> dict:
    eid = event["event_id"]
    etype = event["event_type"]

    if etype == "READ":
        chapter = _parse_chapter(event.get("stage_input", ""))
        prior = _read_notes(notes_path)
        text, tin, tout = _call_llm(
            client, model, READ_SYSTEM_PROMPT,
            _read_user_prompt(prior, chapter),
        )
        new_notes = _extract_notes(text)
        _write_notes_atomic(notes_path, new_notes)
        return {
            "event_id": eid,
            "stage_output": "",
            "tokens_in": tin,
            "tokens_out": tout,
            "api_call_count": 1,
            "model_id": model,
            "notes": f"notes file now {len(new_notes)} chars",
        }

    if etype == "QUIZ":
        questions = _parse_questions(event.get("stage_input", ""))
        if not questions:
            return {"event_id": eid, "answers": [],
                    "notes": "no <QUESTION> tags found in stage_input"}
        notes = _read_notes(notes_path)
        text, tin, tout = _call_llm(
            client, model, QUIZ_SYSTEM_PROMPT,
            _quiz_user_prompt(notes, questions),
        )
        return {
            "event_id": eid,
            "answers": _extract_answers(text),
            "tokens_in": tin,
            "tokens_out": tout,
            "api_call_count": 1,
            "model_id": model,
        }

    return {"event_id": eid, "stage_output": "",
            "notes": f"unknown event_type: {etype}"}


def _iter_events(stream: Iterable[str]):
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _die("OPENROUTER_API_KEY is not set; refusing to start.", code=2)

    try:
        import openai  # type: ignore
    except ImportError:
        _die("`openai` package is not installed (pip install openai).",
             code=2)

    model = os.environ.get("NOTES_LLM_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("RETENTION_BENCH_BASE_URL", DEFAULT_BASE_URL)
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    notes_path = Path.cwd() / NOTES_FILENAME

    for event in _iter_events(sys.stdin):
        response = _handle_event(client, model, notes_path, event)
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
