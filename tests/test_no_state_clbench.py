"""Drive the no-state (ephemeral) floor SUT through gain_curve.

Mirrors ``test_associative_memory_clbench.py`` but asserts the *opposite* of the
retainer: the no-state SUT learns within an episode (``C > P``) yet collapses to
the prior floor across every hard RESET (``R(k) ≈ P``, normalised gain ≈ 0).
"""

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
NO_STATE_PKG = REPO_ROOT / "suts" / "no_state"
NO_STATE_CMD = ["python", "-m", "no_state.clbench_main"]


def _make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
    return SubprocessSystem(
        NO_STATE_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe,
        name="no-state",
        extra_pythonpath=[NO_STATE_PKG],
    )


def _make_task():
    return get_task_class("symbolic_associative_retention")()


def _sweep():
    return run_reset_sweep(
        _make_system,
        _make_task,
        [EveryNInstances(2), EveryNInstances(1)],
        system_name="no-state",
        state_root=Path(tempfile.mkdtemp(prefix="rb4-")),
    )


def test_no_state_learns_within_episode():
    """The ceiling (k=0) is above the prior: within-process learning is real."""
    curve = _sweep()
    assert curve.ceiling > curve.prior
    assert not curve.excluded
    # Same task as associative_memory, so the band is identical: C above the
    # wiped stateless prior.
    assert curve.ceiling == pytest.approx(64 / 112)
    assert curve.prior == pytest.approx(0.0)


def test_no_state_collapses_across_hard_resets():
    """Every hard-reset arm sits at the prior floor: nothing survives the kill."""
    curve = _sweep()
    assert curve.points
    for point in curve.points:
        assert point.k > 0
        # No persistence -> each post-reset process starts empty -> floor.
        assert point.mean_reward == pytest.approx(curve.prior)
        assert point.normalised_gain == pytest.approx(0.0)
        assert point.clbench_mean_gain == pytest.approx(0.0)
