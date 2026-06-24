"""Event-loop entrypoint for the constructive (train-and-grow) SUT.

Reads JSONL events from stdin (per docs/sut-interface.md), responds on stdout.
cwd == DIR (the per-run persistent directory).

  READ : bounded gradient step on the READ text; maybe grow capacity; FLUSH a
         checkpoint to DIR *before* writing the READ ack (so it survives a
         RESET that immediately follows); ack.
  QUIZ : greedy-generate a (gibberish-acceptable) answer per question from the
         current weights; emit a structured `answers` list.

Cold vs. resume: on spawn the SUT checks DIR for a checkpoint. Present → resume
(rebuild grown shape from saved config, load weights). Absent → cold init.

Self-reports param_count / train_steps / train_flops / growth_count via the
free-form `notes` response field (no harness change — see B13 decisions).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

from . import checkpoint as ckpt
from . import train as trainer
from .model import ModelConfig, grow, text_to_ids

# Deterministic growth policy: grow capacity once, on the first READ of the
# whole run (growth_count starts at 0). Simple, auditable, guarantees exactly
# one storage-delta>0 event + a variable-size checkpoint over a session.
GROW_AFTER_READ_INDEX = 1  # grow when this READ (1-based) completes

# Answer generation budget (bytes). Quality is a non-goal; keep it short/fast.
MAX_ANSWER_BYTES = 24

_QUESTION_RE = re.compile(r'<QUESTION\s+id="([^"]+)">(.*?)</QUESTION>', re.DOTALL)
_TEXT_RE = re.compile(r"<TEXT>\s*(.*?)\s*</TEXT>", re.DOTALL)


def _die(msg: str, code: int = 1) -> None:
    print(f"constructive SUT: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def _dir_path() -> Path:
    # cwd is DIR per the contract; RETENTION_BENCH_DIR is a belt-and-braces echo.
    return Path(os.environ.get("RETENTION_BENCH_DIR", os.getcwd()))


def _default_config() -> ModelConfig:
    """Allow env overrides for tiny test configs; defaults stay smoke-safe."""
    def _int(name: str, default: int) -> int:
        v = os.environ.get(name)
        return int(v) if v else default

    return ModelConfig(
        block_size=_int("CONSTRUCTIVE_BLOCK_SIZE", 64),
        d_model=_int("CONSTRUCTIVE_D_MODEL", 64),
        n_heads=_int("CONSTRUCTIVE_N_HEADS", 4),
        n_layers=_int("CONSTRUCTIVE_N_LAYERS", 2),
    )


def _load_state(dir_path: Path) -> ckpt.State:
    seed = int(os.environ.get("CONSTRUCTIVE_SEED", "0"))
    if ckpt.has_checkpoint(dir_path):
        return ckpt.load(dir_path)
    return ckpt.cold_init(_default_config(), seed=seed)


def _parse_read_text(stage_input: str) -> str:
    m = _TEXT_RE.search(stage_input)
    return m.group(1) if m else ""


def _parse_questions(stage_input: str) -> list[tuple[str, str]]:
    return [(q, t.strip()) for q, t in _QUESTION_RE.findall(stage_input)]


def _notes(state: ckpt.State, extra: str = "") -> str:
    m = state.meta
    base = (
        f"param_count={state.model.param_count()} "
        f"train_steps={m.train_steps} train_flops={m.train_flops} "
        f"growth_count={m.growth_count} n_layers={state.config.n_layers}"
    )
    return f"{base} {extra}".strip()


def _handle_read(state: ckpt.State, dir_path: Path, event: dict) -> tuple[dict, ckpt.State]:
    eid = event["event_id"]
    text = _parse_read_text(event.get("stage_input", ""))
    ids = text_to_ids(text)

    steps = trainer.train_on_text(state, ids)
    state.meta.read_count += 1

    grew = False
    if state.meta.read_count == GROW_AFTER_READ_INDEX:
        state.model = grow(state.config, state.model)
        state.config = state.model.cfg
        state.meta.growth_count += 1
        grew = True

    # FLUSH the checkpoint BEFORE writing the ack — survives an immediate RESET.
    ckpt.save(dir_path, state)

    extra = f"steps_this_read={steps}" + (" grew=1" if grew else "")
    return (
        {"event_id": eid, "stage_output": "", "notes": _notes(state, extra)},
        state,
    )


def _handle_quiz(state: ckpt.State, event: dict) -> dict:
    eid = event["event_id"]
    questions = _parse_questions(event.get("stage_input", ""))
    if not questions:
        return {"event_id": eid, "answers": [],
                "notes": "no <QUESTION> tags found in stage_input"}

    answers = []
    for qid, qtext in questions:
        prompt = text_to_ids(qtext + "\n")
        gen = state.model.generate(prompt, max_new_tokens=MAX_ANSWER_BYTES)
        # Decode bytes back to text; replace undecodable bytes (gibberish ok).
        ans = bytes(b for b in gen if 0 <= b < 256).decode("utf-8", errors="replace").strip()
        answers.append({"id": qid, "text": ans})

    return {"event_id": eid, "answers": answers, "notes": _notes(state)}


def _iter_events(stream: Iterable[str]):
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        _die("`torch` is not installed (pip install torch). CPU build is fine.",
             code=2)

    dir_path = _dir_path()
    state = _load_state(dir_path)

    for event in _iter_events(sys.stdin):
        eid = event.get("event_id", "")
        etype = event.get("event_type", "")
        if etype == "READ":
            response, state = _handle_read(state, dir_path, event)
        elif etype == "QUIZ":
            response = _handle_quiz(state, event)
        else:
            response = {"event_id": eid, "stage_output": "",
                        "notes": f"unknown event_type: {etype}"}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
