"""End-to-end integration test for the notes-llm SUT.

Drives the real harness against the real `suts/notes_llm/` SUT, with the
`anthropic` SDK replaced by the PYTHONPATH-shadowing fake shim (same
pattern as test_no_state_fake_anthropic.py). Runs in CI without
ANTHROPIC_API_KEY or network access.

The fixture (two_chapter.yaml) drives: READ ch1, READ ch2, QUIZ ceiling,
RESET, QUIZ retention k=1. With the canned shim responses, this gives
full retention — both questions answered correctly after RESET — because
notes survived on disk.

Load-bearing assertions:
  - notes.md is written after each READ (cumulative path works).
  - notes.md survives RESET (DIR persistence works end-to-end).
  - The post-RESET QUIZ extracts answers from the persisted notes, not
    from chapter text (the SUT no longer has chapter text to fall back on).
  - Resource aggregation sums across all 4 LLM calls, including the 2
    pre-RESET calls + 2 post-RESET-boundary calls (proves the M7 fix is
    still in place for notes-llm too).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import __main__ as harness_main


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "two_chapter.yaml"
NOTES_LLM_DIR = REPO_ROOT / "suts" / "notes_llm"
FAKE_SHIM_DIR = REPO_ROOT / "tests" / "fake_anthropic_shim"
RESPONSES_YAML = (
    REPO_ROOT / "tests" / "fixtures" / "fake_anthropic_notes_llm_responses.yaml"
)

# Must match fake_anthropic_notes_llm_responses.yaml exactly.
EXPECTED_TOKENS_IN = 101 + 211 + 131 + 137
EXPECTED_TOKENS_OUT = 41 + 79 + 23 + 29
EXPECTED_API_CALLS = 4


def test_notes_llm_with_fake_anthropic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = tmp_path / "fake_anthropic.counter"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-not-real")
    monkeypatch.setenv("FAKE_ANTHROPIC_FIXTURE", str(RESPONSES_YAML))
    monkeypatch.setenv("FAKE_ANTHROPIC_COUNTER", str(counter))
    existing = __import__("os").environ.get("PYTHONPATH", "")
    new_pp = str(FAKE_SHIM_DIR) + (":" + existing if existing else "")
    monkeypatch.setenv("PYTHONPATH", new_pp)

    runs_dir = tmp_path / "runs"
    rc = harness_main.main([
        str(FIXTURE),
        "--sut", str(NOTES_LLM_DIR),
        "--runs-dir", str(runs_dir),
        "--run-id", "notes-llm-fake",
    ])
    assert rc == 0

    run_dir = runs_dir / "notes-llm-fake"
    assert run_dir.is_dir()

    # Trace shape: READ, READ, QUIZ, RESET, QUIZ.
    events = [
        json.loads(l)
        for l in (run_dir / "trace.jsonl").read_text().splitlines()
    ]
    assert [e["event_type"] for e in events] == [
        "READ", "READ", "QUIZ", "RESET", "QUIZ",
    ]

    # Two SUT subprocesses (initial + post-RESET).
    rm = json.loads((run_dir / "run-manifest.json").read_text())
    assert rm["exit_status"] == "ok"
    assert rm["reset_count"] == 1
    assert rm["sut_invocation_count"] == 2

    # All 4 LLM calls landed (2 READs + 2 QUIZs, the second QUIZ proves the
    # post-RESET subprocess imported the shim, not the real SDK).
    assert counter.read_text().strip() == str(EXPECTED_API_CALLS)

    # Resource aggregation across all four calls and across the RESET
    # boundary — same regression coverage as test_no_state_fake_anthropic
    # but verifying it for the second reference SUT too.
    sm = json.loads((run_dir / "sut-manifest.json").read_text())
    ra = sm["resource_appendix"]
    assert ra["tokens_in"] == EXPECTED_TOKENS_IN
    assert ra["tokens_out"] == EXPECTED_TOKENS_OUT
    assert ra["api_call_count"] == EXPECTED_API_CALLS
    assert ra["model_id"] == "claude-haiku-4-5-20251001"

    # Per-question records: full retention since the fake faithfully echoes
    # notes-derived answers in both QUIZ events.
    qrecs = [
        json.loads(l)
        for l in (run_dir / "questions.jsonl").read_text().splitlines()
    ]
    assert len(qrecs) == 4  # 2 questions x 2 quizzes
    by_event = {(r["event_id"], r["question_id"]): r for r in qrecs}
    # Ceiling — both correct, both questions, from notes.md.
    assert by_event[("evt-0003", "q1")]["sut_answer"] == "Mira Vexin"
    assert by_event[("evt-0003", "q2")]["sut_answer"] == "Halton Reeve"
    # Retention (post-RESET) — same correct answers, proving notes
    # survived RESET on disk.
    assert by_event[("evt-0005", "q1")]["sut_answer"] == "Mira Vexin"
    assert by_event[("evt-0005", "q2")]["sut_answer"] == "Halton Reeve"
    for r in qrecs:
        assert r["parsing_status"] == "ok"

    # The DIR must contain a non-empty notes.md after the run; it must
    # mention both chapters' content (Mira Vexin from ch1 + Halton Reeve
    # from ch2) — proves the cumulative-notes path works end-to-end.
    dir_path = run_dir / "dir"
    notes_path = dir_path / "notes.md"
    assert notes_path.is_file(), f"notes.md missing under {dir_path}"
    notes_text = notes_path.read_text()
    assert "Mira Vexin" in notes_text
    assert "Halton Reeve" in notes_text
