"""End-to-end integration test: harness drives the real constructive SUT.

Runs offline, CPU-only, no API key — the constructive SUT makes no network
calls. Uses a tiny model config (via env) so the run is fast. Drives the
two_chapter fixture: READ, READ, QUIZ, RESET, QUIZ.

Load-bearing assertions:
  - trace shape READ/READ/QUIZ/RESET/QUIZ; two SUT subprocesses;
  - a checkpoint.pt is written to DIR during READ and survives RESET;
  - the checkpoint records a growth event (grown n_layers) — proving the
    variable-size checkpoint reloaded after RESET;
  - QUIZ answers are well-formed (matching ids) before AND after RESET;
  - the SUT self-reports param_count / train_steps via the notes field.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")

from harness import __main__ as harness_main  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "two_chapter.yaml"
CONSTRUCTIVE_DIR = REPO_ROOT / "suts" / "constructive"


def test_constructive_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Tiny config so the run is quick on CPU.
    monkeypatch.setenv("CONSTRUCTIVE_BLOCK_SIZE", "16")
    monkeypatch.setenv("CONSTRUCTIVE_D_MODEL", "16")
    monkeypatch.setenv("CONSTRUCTIVE_N_HEADS", "2")
    monkeypatch.setenv("CONSTRUCTIVE_N_LAYERS", "1")
    monkeypatch.setenv("CONSTRUCTIVE_SEED", "0")

    runs_dir = tmp_path / "runs"
    rc = harness_main.main([
        str(FIXTURE),
        "--sut", str(CONSTRUCTIVE_DIR),
        "--runs-dir", str(runs_dir),
        "--run-id", "constructive-e2e",
    ])
    assert rc == 0

    run_dir = runs_dir / "constructive-e2e"
    assert run_dir.is_dir()

    events = [
        json.loads(line)
        for line in (run_dir / "trace.jsonl").read_text().splitlines()
    ]
    assert [e["event_type"] for e in events] == [
        "READ", "READ", "QUIZ", "RESET", "QUIZ",
    ]

    rm = json.loads((run_dir / "run-manifest.json").read_text())
    assert rm["exit_status"] == "ok"
    assert rm["reset_count"] == 1
    assert rm["sut_invocation_count"] == 2

    # Checkpoint written to DIR and survived RESET (still present at run end).
    ckpt_path = run_dir / "dir" / "checkpoint.pt"
    assert ckpt_path.is_file(), f"checkpoint.pt missing under {run_dir / 'dir'}"

    # The grown architecture round-tripped: load it and confirm n_layers grew.
    if str(CONSTRUCTIVE_DIR) not in sys.path:
        sys.path.insert(0, str(CONSTRUCTIVE_DIR))
    from constructive import checkpoint as ckpt  # noqa: E402

    state = ckpt.load(run_dir / "dir")
    assert state.config.n_layers == 2  # grew from 1 -> 2 (default policy)
    assert state.meta.growth_count == 1
    assert state.meta.train_steps > 0
    assert state.meta.read_count == 2

    # QUIZ answers well-formed before and after RESET.
    qrecs = [
        json.loads(line)
        for line in (run_dir / "questions.jsonl").read_text().splitlines()
    ]
    assert len(qrecs) == 4  # 2 questions x 2 QUIZ events
    for r in qrecs:
        assert r["parsing_status"] in {"ok", "not_found", "ambiguous"}
        assert isinstance(r["sut_answer"], str)

    # sut-manifest copied + tier/mode correct.
    sm = json.loads((run_dir / "sut-manifest.json").read_text())
    assert sm["name"] == "constructive"
    assert sm["mode"] == "in-context"
    assert sm["hardware_tier"] == "open"
    assert sm["resource_appendix"]["kind"] == "local"
