"""End-to-end smoke: drive the stub SUT through a tiny task and verify the trace."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness import event_loop, task_loader


TASK_YAML = """
task_id: stub-smoke
schema_version: 1
description: stub smoke
materials:
  - id: m1
    text: "Gregor is a salesman."
questions:
  - id: q1
    text: "profession?"
    gold: "salesman"
    type: surface_factual
    material_ref: m1
  - id: q2
    text: "name?"
    gold: "Gregor"
    type: surface_factual
    material_ref: m1
events:
  - type: quiz
    questions: [q1, q2]
    probe: prior
  - type: read
    material_id: m1
  - type: quiz
    questions: [q1, q2]
    probe: ceiling
  - type: reset
  - type: quiz
    questions: [q1, q2]
    probe: retention
    k: 1
"""


def _write_task(tmp_path: Path) -> Path:
    p = tmp_path / "task.yaml"
    p.write_text(TASK_YAML, encoding="utf-8")
    return p


def test_stub_run_end_to_end(tmp_path: Path) -> None:
    task_path = _write_task(tmp_path)
    task = task_loader.load_task(task_path)
    runs_root = tmp_path / "runs"
    config = event_loop.RunConfig(
        task=task,
        sut_command=[sys.executable, "-m", "harness.stubs.echo_sut"],
        runs_root=runs_root,
        run_id="stub-smoke-test",
    )
    run_dir = event_loop.run(config)
    assert run_dir.is_dir()

    trace_lines = (run_dir / "trace.jsonl").read_text().splitlines()
    q_lines = (run_dir / "questions.jsonl").read_text().splitlines()
    assert len(trace_lines) == 5  # 3 quizzes + 1 read + 1 reset
    assert len(q_lines) == 2 * 3   # 2 questions x 3 quizzes

    events = [json.loads(l) for l in trace_lines]
    types = [e["event_type"] for e in events]
    assert types == ["QUIZ", "READ", "QUIZ", "RESET", "QUIZ"]

    reset_evt = events[3]
    for field in [
        "snapshot_path", "dir_uncompressed_bytes", "dir_file_count",
        "dir_tarball_bytes", "sut_kill_signal",
    ]:
        assert field in reset_evt
    assert (run_dir / reset_evt["snapshot_path"]).is_file()

    # SUT process ids change across RESET.
    first_quiz = events[0]["sut_process_id"]
    third_quiz = events[4]["sut_process_id"]
    assert first_quiz != third_quiz

    # Per-question records built by structural lookup over the stub's
    # `answers` list (no text parsing — M4 contract).
    qrecs = [json.loads(l) for l in q_lines]
    assert all(r["parsing_status"] == "ok" for r in qrecs)
    assert all(r["sut_answer"] == "STUB_ANSWER" for r in qrecs)

    # question_seen_before increments per question across probes.
    by_qid_seen = {}
    for r in qrecs:
        by_qid_seen.setdefault(r["question_id"], []).append(r["question_seen_before"])
    assert by_qid_seen["q1"] == [0, 1, 2]
    assert by_qid_seen["q2"] == [0, 1, 2]

    # Manifests exist with expected shape.
    rm = json.loads((run_dir / "run-manifest.json").read_text())
    assert rm["task_id"] == "stub-smoke"
    assert rm["reset_count"] == 1
    assert rm["sut_invocation_count"] == 2
    assert rm["event_count"] == 5
    assert rm["exit_status"] == "ok"

    sm = json.loads((run_dir / "sut-manifest.json").read_text())
    assert "name" in sm
