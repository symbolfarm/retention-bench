"""End-to-end CLI test for ``python -m scorer <run-dir>``.

Also exercises the purity property: same input → byte-identical output.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_records(run_dir: Path, records: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "questions.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _rec(qid: str, probe: str, sut: str, gold: str, k: int | None = None) -> dict:
    return {
        "record_id": f"evt-{qid}-{probe}",
        "event_id": f"evt-{probe}",
        "question_id": qid,
        "probe_type": probe,
        "k": k,
        "question_text": "?",
        "gold_answer": gold,
        "sut_answer": sut,
        "question_type": "surface_factual",
        "material_ref": "m1",
        "question_seen_before": 0,
        "parsing_status": "ok",
    }


def _run(run_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scorer", str(run_dir)],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_smoke(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        _rec("q1", "retention", "right", "right", k=1),
        _rec("q2", "prior", "right", "right"),  # excluded — C≈P
        _rec("q2", "ceiling", "right", "right"),
        _rec("q2", "retention", "right", "right", k=1),
    ]
    _write_records(run_dir, records)

    result = _run(run_dir)
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "question_id" in out
    assert "q1" in out and "q2" in out
    assert "excluded" in out  # q2 is C≈P
    assert "aggregate (k=1, n_usable=1): 1.00" in out
    # Per-question_type breakdown (B15): both records are surface_factual.
    assert "by question_type:" in out
    assert "surface_factual (k=1, n_usable=1): 1.00" in out


def test_cli_deterministic(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        _rec("q1", "retention", "right", "right", k=1),
        _rec("q2", "prior", "wrong", "right"),
        _rec("q2", "ceiling", "right", "right"),
        _rec("q2", "retention", "wrong", "right", k=1),
    ]
    _write_records(run_dir, records)

    a = _run(run_dir).stdout
    b = _run(run_dir).stdout
    assert a == b  # Byte-identical on re-run — purity check.


def test_cli_missing_questions_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "empty"
    run_dir.mkdir()
    result = _run(run_dir)
    assert result.returncode == 2
    assert "missing questions.jsonl" in result.stderr


def test_cli_not_a_directory(tmp_path: Path) -> None:
    path = tmp_path / "nope"
    result = _run(path)
    assert result.returncode == 2
    assert "not a directory" in result.stderr
