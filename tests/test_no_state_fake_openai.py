"""End-to-end integration test driving the real harness against the real
no-state SUT, with `openai` replaced by a PYTHONPATH-shadowing fake.

Unlike test_no_state_integration.py, this runs without OPENROUTER_API_KEY and
without hitting the live API, so it runs in CI. It exercises the full
subprocess + SDK + token-accounting path that the stub-SUT unit tests miss.

Regression coverage:
  - M7 bug: `_run_reset` previously dropped PYTHONPATH on respawn, so the
    second SUT subprocess would have failed to import the fake. If that
    regresses, the second QUIZ would either crash the SUT or hit the real
    openai SDK with a fake key and fail.
  - M7 bug: SUT-reported resource fields (tokens_in, tokens_out,
    api_call_count) were dropped before being written into the trace. This
    test asserts the exact aggregate that only matches if both subprocess
    responses' fields flowed through end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import __main__ as harness_main


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "trivial.yaml"
NO_STATE_DIR = REPO_ROOT / "suts" / "no_state"
FAKE_SHIM_DIR = REPO_ROOT / "tests" / "fake_openai_shim"
RESPONSES_YAML = REPO_ROOT / "tests" / "fixtures" / "fake_no_state_responses.yaml"

# Must match fake_no_state_responses.yaml exactly.
EXPECTED_TOKENS_IN = 142 + 30
EXPECTED_TOKENS_OUT = 23 + 16
EXPECTED_API_CALLS = 2


def test_no_state_with_fake_openai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    counter = tmp_path / "fake_openai.counter"
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-not-real")
    monkeypatch.setenv("FAKE_OPENAI_FIXTURE", str(RESPONSES_YAML))
    monkeypatch.setenv("FAKE_OPENAI_COUNTER", str(counter))
    # Prepend the shim dir to PYTHONPATH so the SUT subprocess imports our
    # fake `openai` instead of the installed one. Harness propagates env
    # via os.environ.copy(), so monkeypatch.setenv is sufficient.
    existing = __import__("os").environ.get("PYTHONPATH", "")
    new_pp = str(FAKE_SHIM_DIR) + (":" + existing if existing else "")
    monkeypatch.setenv("PYTHONPATH", new_pp)

    runs_dir = tmp_path / "runs"
    rc = harness_main.main([
        str(FIXTURE),
        "--sut", str(NO_STATE_DIR),
        "--runs-dir", str(runs_dir),
        "--run-id", "no-state-fake",
    ])
    assert rc == 0

    run_dir = runs_dir / "no-state-fake"
    assert run_dir.is_dir()

    # Trace shape: READ, QUIZ, RESET, QUIZ.
    events = [json.loads(l) for l in (run_dir / "trace.jsonl").read_text().splitlines()]
    assert [e["event_type"] for e in events] == ["READ", "QUIZ", "RESET", "QUIZ"]

    # Two SUT subprocesses were spawned (initial + post-RESET).
    rm = json.loads((run_dir / "run-manifest.json").read_text())
    assert rm["exit_status"] == "ok"
    assert rm["reset_count"] == 1
    assert rm["sut_invocation_count"] == 2

    # Both QUIZ subprocesses successfully called the fake — counter advanced
    # by 2. This is the load-bearing assertion for the PYTHONPATH-on-respawn
    # regression: if the second SUT had dropped PYTHONPATH and crashed (or
    # gone to the real SDK), this counter would be 1, not 2.
    assert counter.read_text().strip() == str(EXPECTED_API_CALLS)

    # Resource aggregation: exact synthetic values, summed across both calls.
    # Regression for the M7 dropped-resource-fields bug — these only land
    # correctly if `_run_quiz` reads SUT-reported fields *and*
    # `_finalize_sut_manifest` writes them into resource_appendix.
    sm = json.loads((run_dir / "sut-manifest.json").read_text())
    ra = sm["resource_appendix"]
    assert ra["tokens_in"] == EXPECTED_TOKENS_IN
    assert ra["tokens_out"] == EXPECTED_TOKENS_OUT
    assert ra["api_call_count"] == EXPECTED_API_CALLS
    assert ra["model_id"] == "deepseek/deepseek-v4-flash"
    assert ra["wall_clock_ms"] >= 0

    # Per-question records: the fake's <ANSWER> tags parsed back out.
    qrecs = [json.loads(l) for l in (run_dir / "questions.jsonl").read_text().splitlines()]
    assert len(qrecs) == 4  # 2 questions x 2 quizzes
    by_event = {(r["event_id"], r["question_id"]): r for r in qrecs}
    # Ceiling quiz answers from response[0].
    assert by_event[("evt-0002", "q1")]["sut_answer"] == "Coral City"
    assert by_event[("evt-0002", "q2")]["sut_answer"] == "Mira Vexin"
    # Retention quiz answers from response[1] — note Unknown, confirming the
    # second subprocess used the fake (not a cached or repeated response).
    assert by_event[("evt-0004", "q1")]["sut_answer"] == "Unknown"
    assert by_event[("evt-0004", "q2")]["sut_answer"] == "Unknown"
    for r in qrecs:
        assert r["parsing_status"] == "ok"
