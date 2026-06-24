"""RB-2c: drive the associative-memory reference SUT through gain_curve."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from retention_bench import EveryNInstances  # noqa: E402
from retention_bench._clbench import get_task_class  # noqa: E402
from retention_bench.gain_curve import run_reset_sweep  # noqa: E402
from retention_bench.system import SubprocessSystem  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSOCIATIVE_MEMORY_PKG = REPO_ROOT / "suts" / "associative_memory"
ASSOCIATIVE_MEMORY_CMD = ["python", "-m", "associative_memory.clbench_main"]


def _make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
    return SubprocessSystem(
        ASSOCIATIVE_MEMORY_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe,
        name="associative-memory",
        extra_pythonpath=[ASSOCIATIVE_MEMORY_PKG],
    )


def _make_task():
    return get_task_class("symbolic_associative_retention")()


def _sweep():
    return run_reset_sweep(
        _make_system,
        _make_task,
        [EveryNInstances(2), EveryNInstances(1)],
        system_name="associative-memory",
        state_root=Path(tempfile.mkdtemp(prefix="rb2c-")),
    )


def test_associative_memory_shows_retention_band():
    curve = _sweep()
    assert curve.ceiling > curve.prior
    assert not curve.excluded
    assert curve.ceiling == pytest.approx(16 / 26)
    assert curve.prior == pytest.approx(0.0)


def test_associative_memory_survives_hard_resets():
    curve = _sweep()
    assert curve.points
    for point in curve.points:
        assert point.k > 0
        assert point.mean_reward == pytest.approx(curve.ceiling)
        assert point.normalised_gain == pytest.approx(1.0)
        assert point.clbench_mean_gain == pytest.approx(curve.band)
