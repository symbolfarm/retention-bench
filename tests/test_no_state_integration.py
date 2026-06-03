"""End-to-end integration test: harness drives the real no-state SUT against
the trivial fixture, calls the OpenAI-compatible API (OpenRouter) for real,
and produces a valid trace + snapshot + per-question records.

Skipped unless OPENROUTER_API_KEY is set — CI does not have a key; local runs do.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from harness import __main__ as harness_main


pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set; skipping live no-state SUT integration",
)


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "trivial.yaml"
NO_STATE_DIR = REPO_ROOT / "suts" / "no_state"


def _have_openai() -> bool:
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _have_openai(), reason="openai package not installed")
def test_no_state_end_to_end(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    argv = [
        str(FIXTURE),
        "--sut", str(NO_STATE_DIR),
        "--runs-dir", str(runs_dir),
        "--run-id", "no-state-integration",
    ]
    rc = harness_main.main(argv)
    assert rc == 0

    run_dir = runs_dir / "no-state-integration"
    assert run_dir.is_dir()

    trace_lines = (run_dir / "trace.jsonl").read_text().splitlines()
    q_lines = (run_dir / "questions.jsonl").read_text().splitlines()
    assert len(trace_lines) == 4   # READ + QUIZ + RESET + QUIZ
    assert len(q_lines) == 4       # 2 questions x 2 quizzes

    events = [json.loads(l) for l in trace_lines]
    assert [e["event_type"] for e in events] == ["READ", "QUIZ", "RESET", "QUIZ"]

    # The no-state SUT can't see the text after RESET, so the retention quiz
    # should be "not_found" or wrong. We don't assert on correctness here —
    # we just assert the contract held.
    qrecs = [json.loads(l) for l in q_lines]
    for r in qrecs:
        assert r["parsing_status"] in {"ok", "not_found", "ambiguous"}
        assert isinstance(r["sut_answer"], str)

    # sut-manifest copied from the SUT package
    sm = json.loads((run_dir / "sut-manifest.json").read_text())
    assert sm["name"] == "no-state"
    assert sm["mode"] == "in-context"
    assert sm["entrypoint"][0] == "python"

    rm = json.loads((run_dir / "run-manifest.json").read_text())
    assert rm["exit_status"] == "ok"
    assert rm["reset_count"] == 1
