"""Drive the bounded-memory reference SUT through gain_curve + assert eviction.

bounded_memory is the partial-retention rung: it persists a capped FIFO window of
the most recent facts. Its retention band sits strictly between the no_state floor
(R=0) and the full retainer associative_memory (R=16/26).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from pydantic import BaseModel  # noqa: E402

from retention_bench import EveryNInstances  # noqa: E402
from retention_bench._clbench import Query  # noqa: E402
from retention_bench._clbench import get_task_class  # noqa: E402
from retention_bench.gain_curve import run_reset_sweep  # noqa: E402
from retention_bench.system import SubprocessSystem  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
BOUNDED_MEMORY_PKG = REPO_ROOT / "suts" / "bounded_memory"
BOUNDED_MEMORY_CMD = ["python", "-m", "bounded_memory.clbench_main"]

# Default cap is 8; symbolic_associative_retention trains 10 facts, so the two
# oldest object facts are evicted -> 12/26 of the probes survive.
PARTIAL_CEILING = 12 / 26
FULL_CEILING = 16 / 26


class _Answer(BaseModel):
    answer: str


def _make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
    return SubprocessSystem(
        BOUNDED_MEMORY_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe,
        name="bounded-memory",
        extra_pythonpath=[BOUNDED_MEMORY_PKG],
    )


def _make_task():
    return get_task_class("symbolic_associative_retention")()


def _sweep():
    return run_reset_sweep(
        _make_system,
        _make_task,
        [EveryNInstances(2), EveryNInstances(1)],
        system_name="bounded-memory",
        state_root=Path(tempfile.mkdtemp(prefix="rb5-")),
    )


def test_bounded_memory_partial_retention_band():
    curve = _sweep()
    assert curve.ceiling > curve.prior
    assert not curve.excluded
    assert curve.prior == pytest.approx(0.0)
    # Partial: strictly between the no_state floor (0) and the full retainer.
    assert curve.ceiling == pytest.approx(PARTIAL_CEILING)
    assert 0.0 < curve.ceiling < FULL_CEILING


def test_bounded_memory_retains_window_across_resets():
    curve = _sweep()
    assert curve.points
    for point in curve.points:
        assert point.k > 0
        # State survives the hard reset, so the window is held at the (capped)
        # ceiling rather than collapsing to the floor.
        assert point.mean_reward == pytest.approx(curve.ceiling)
        assert point.normalised_gain == pytest.approx(1.0)


def _query(prompt: str, idx: int) -> Query:
    return Query(
        prompt=prompt,
        response_schema=_Answer,
        instance_id=f"bm-{idx:04d}",
        instance_index=idx,
    )


def _train_object(obj: str, attr: str, idx: int) -> Query:
    return _query(
        f"TRAIN object_attribute\nobject: {obj}\nattribute: {attr}\nReply exactly: stored",
        idx,
    )


def _recall_object(obj: str, idx: int) -> Query:
    return _query(
        f"RECALL object_attribute\nobject: {obj}\n"
        "What attribute was taught for this object? Reply with the attribute only.",
        idx,
    )


def test_bounded_memory_evicts_oldest_fact_across_reset(monkeypatch):
    """With cap=2, the 3rd trained fact evicts the 1st; only recent ones survive."""
    monkeypatch.setenv("BOUNDED_MEMORY_CAP", "2")
    state_dir = Path(tempfile.mkdtemp(prefix="rb5-evict-"))
    system = _make_system(state_dir, EveryNInstances(1), wipe=False)
    try:
        # Train three facts; cap=2 means "old" is evicted, "mid"/"new" survive.
        system.respond(_train_object("old", "red", 0))
        system.respond(_train_object("mid", "blue", 1))
        system.respond(_train_object("new", "red", 2))

        # Hard-bounce: only the on-disk capped window persists.
        system.reset()

        assert system.respond(_recall_object("old", 3)).action.answer == "unknown"
        assert system.respond(_recall_object("mid", 4)).action.answer == "blue"
        assert system.respond(_recall_object("new", 5)).action.answer == "red"
    finally:
        system.shutdown()
