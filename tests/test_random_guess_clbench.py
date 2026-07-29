"""RB-16: drive the random-guess chance rung through gain_curve.

This rung exists so the guessing floor is *measured* rather than inferred. The
assertions pin the two things that make it useful: (a) it is flat — prior,
ceiling and every ``R(k)`` are the same number, so the band is EXCLUDED and the
line is a genuine chance line rather than a retention curve; and (b) it sits far
below the graded ``reset_lossy`` rung, which is exactly what the pre-RB-16
two-way task failed to do (a constant guesser scored 0.308 there, colliding with
``reset_lossy``'s published ``R(k=12)``).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from retention_bench import EveryNInstances  # noqa: E402
from retention_bench._clbench import get_task_class  # noqa: E402
from retention_bench.gain_curve import run_reset_sweep  # noqa: E402
from retention_bench.system import SubprocessSystem  # noqa: E402
from retention_bench.tasks.symbolic_associative_retention import (  # noqa: E402
    SymbolicAssociativeRetentionTask,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RANDOM_GUESS_PKG = REPO_ROOT / "suts" / "random_guess"
RANDOM_GUESS_CMD = ["python", "-m", "random_guess.clbench_main"]

# random_guess is not installed in the venv; put the package dir on sys.path so
# the vocabulary-drift test can import it in-process.
if str(RANDOM_GUESS_PKG) not in sys.path:
    sys.path.insert(0, str(RANDOM_GUESS_PKG))

# One fixed draw at seed 0 over the default 16-wide schedule: 3 of 64 probes land
# on the right answer, i.e. 3/112 run-mean. Analytic chance is 1/16 per probe
# (4/112 run-mean); the gap is the sampling noise of a single deterministic draw.
EXPECTED_R = 3 / 112
ANALYTIC_CHANCE = 1 / 16


def _make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
    return SubprocessSystem(
        RANDOM_GUESS_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe,
        name="random-guess",
        extra_pythonpath=[RANDOM_GUESS_PKG],
    )


def _make_task():
    return get_task_class("symbolic_associative_retention")()


def _sweep():
    return run_reset_sweep(
        _make_system,
        _make_task,
        [EveryNInstances(2), EveryNInstances(1)],
        system_name="random-guess",
        state_root=Path(tempfile.mkdtemp(prefix="rb16-")),
    )


def test_random_guess_vocabulary_matches_the_task():
    """The SUT duplicates the task's vocabulary to stay dependency-free; drift
    would silently move the chance level, so pin the two together."""
    from random_guess import clbench_main as rg  # noqa: PLC0415

    assert rg.ATTRIBUTES == SymbolicAssociativeRetentionTask._ATTRIBUTES
    assert rg.BINS == SymbolicAssociativeRetentionTask._BINS
    assert rg.DEFAULT_NUM_ATTRIBUTES == SymbolicAssociativeRetentionTask().num_attributes


def test_random_guess_band_is_excluded_and_flat():
    curve = _sweep()
    # Nothing is learned and nothing is retained: P == C, so there is no band.
    assert curve.prior == pytest.approx(curve.ceiling)
    assert curve.excluded
    assert curve.ceiling == pytest.approx(EXPECTED_R)
    for point in curve.points:
        assert point.k > 0
        assert point.mean_reward == pytest.approx(EXPECTED_R)
        assert point.normalised_gain is None
        assert point.clbench_mean_gain == pytest.approx(0.0)


def test_chance_line_sits_far_below_the_graded_rung():
    """The RB-16 correctness criterion, expressed as a test: the guessing floor
    must be unambiguously separated from partial retention. reset_lossy's
    re-measured R(k=55) is 0.3125."""
    curve = _sweep()
    assert curve.ceiling < 0.1
    assert curve.ceiling < 0.3125 / 4
    # And the analytic chance the rung samples is 1/16 per probe.
    assert ANALYTIC_CHANCE * SymbolicAssociativeRetentionTask.r_max == pytest.approx(
        0.0357142857, abs=1e-6
    )
