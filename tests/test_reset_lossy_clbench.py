"""Drive the reset-lossy reference SUT through gain_curve.

Asserts the graded, *decaying* retention curve the rung exists to populate:
``0 < normalised_retention < 1`` at every reset arm, and more resets -> fewer
facts recalled (the ``every_1`` arm sits strictly below ``every_2``). The loss
rate is pinned via ``RESET_LOSSY_RATE`` so the deterministic hash-gate produces a
fixed curve the assertions can pin exactly.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from retention_bench import EveryNInstances  # noqa: E402
from retention_bench._clbench import get_task_class  # noqa: E402
from retention_bench.gain_curve import run_reset_sweep  # noqa: E402
from retention_bench.system import SubprocessSystem  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESET_LOSSY_PKG = REPO_ROOT / "suts" / "reset_lossy"
RESET_LOSSY_CMD = ["python", "-m", "reset_lossy.clbench_main"]

# Pinned rate. Geometric decay + the deterministic hash-gate make these exact.
PINNED_RATE = "0.05"
# every_2 -> k=12 resets at probe time: survivors give 4 recalls + 4 transfers = 8/26.
EXPECTED_R_EVERY_2 = 8 / 26
# every_1 -> k=25 resets at probe time: 3 recalls + 3 transfers = 6/26.
EXPECTED_R_EVERY_1 = 6 / 26


@pytest.fixture(autouse=True)
def _pin_rate():
    prev = os.environ.get("RESET_LOSSY_RATE")
    os.environ["RESET_LOSSY_RATE"] = PINNED_RATE
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("RESET_LOSSY_RATE", None)
        else:
            os.environ["RESET_LOSSY_RATE"] = prev


def _make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
    return SubprocessSystem(
        RESET_LOSSY_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe,
        name="reset-lossy",
        extra_pythonpath=[RESET_LOSSY_PKG],
    )


def _make_task():
    return get_task_class("symbolic_associative_retention")()


def _sweep():
    return run_reset_sweep(
        _make_system,
        _make_task,
        [EveryNInstances(2), EveryNInstances(1)],
        system_name="reset-lossy",
        state_root=Path(tempfile.mkdtemp(prefix="rb7-")),
    )


def test_reset_lossy_ceiling_is_full_band():
    """k=0 (no reset): (1-rate)**0 = 1 -> every fact survives, full band ceiling."""
    curve = _sweep()
    assert not curve.excluded
    assert curve.prior == pytest.approx(0.0)
    assert curve.ceiling == pytest.approx(16 / 26)


def test_reset_lossy_retention_is_graded():
    """Every reset arm lands strictly inside the (0, 1) normalised band."""
    curve = _sweep()
    assert curve.points
    for point in curve.points:
        assert point.k > 0
        assert 0.0 < point.mean_reward < curve.ceiling
        assert 0.0 < point.normalised_gain < 1.0


def test_reset_lossy_decays_with_reset_count():
    """More resets -> fewer facts recalled: every_1 (k=25) below every_2 (k=12)."""
    curve = _sweep()
    by_k = {point.k: point for point in curve.points}
    assert set(by_k) == {12, 25}
    assert by_k[25].mean_reward < by_k[12].mean_reward
    assert by_k[12].mean_reward == pytest.approx(EXPECTED_R_EVERY_2)
    assert by_k[25].mean_reward == pytest.approx(EXPECTED_R_EVERY_1)
