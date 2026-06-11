"""C19: drive the keyless accumulator SUT through CL-Bench's runner.

This is the SUT that backs the offline smoke (`./run.sh smoke`). Unlike the other
reference SUTs it needs **no API key and no torch** — it parses transmitter peaks
out of the rendered prompt and unions them into the survive-dir. So this test
runs fully offline against the real `blind_spectrum_monitoring` task.

The load-bearing claims:

  * the accumulator runs through `SubprocessSystem` on the real task and returns
    valid `ScanReport`s (no contract crash);
  * it produces a **non-degenerate retention band** — the ceiling (state
    accumulates) scores above the stateless prior (survive-dir wiped each
    instance), because accumulation recovers transmitters dormant on any single
    scan;
  * it **retains perfectly across hard resets** — every `R(k)` arm equals the
    ceiling, since the accumulated state survives the RESET SIGKILL on disk. That
    is the whole thesis: a hard reset with a surviving state-dir loses nothing.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from src.tasks.blind_spectrum_monitoring.task import (  # noqa: E402
    BlindSpectrumMonitoringTask,
)

from retention_bench import EveryNInstances  # noqa: E402
from retention_bench.gain_curve import run_reset_sweep  # noqa: E402
from retention_bench.system import SubprocessSystem  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCUMULATOR_PKG = REPO_ROOT / "suts" / "bsm_accumulator"
# "python" is rewritten to sys.executable by spawn_sut; the package is put on the
# subprocess PYTHONPATH so `-m bsm_accumulator.clbench_main` resolves from
# cwd=survive-dir.
ACCUMULATOR_CMD = ["python", "-m", "bsm_accumulator.clbench_main"]

VARIANT = "five_ch_wide"  # 5 active + 8 dormant channels; no frozen corpus needed.
NUM_INSTANCES = 20  # enough scans for dormant channels (p_active=0.1) to surface.


def _make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
    return SubprocessSystem(
        ACCUMULATOR_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe,
        name="bsm-accumulator",
        extra_pythonpath=[ACCUMULATOR_PKG],
    )


def _make_task() -> BlindSpectrumMonitoringTask:
    return BlindSpectrumMonitoringTask(
        variant=VARIANT, num_instances=NUM_INSTANCES, probe_mode=True
    )


def _sweep():
    return run_reset_sweep(
        _make_system,
        _make_task,
        [EveryNInstances(2), EveryNInstances(1)],
        system_name="bsm-accumulator",
        state_root=Path(tempfile.mkdtemp(prefix="c19-")),
    )


def test_accumulator_shows_retention_band():
    """Accumulating across scans beats the stateless prior: ceiling > prior, and
    the band is real (not excluded)."""
    curve = _sweep()
    assert curve.ceiling > curve.prior  # accumulation recovers dormant channels
    assert not curve.excluded  # band >= epsilon → normalised curve is defined
    # Every arm plays the seeded (seed=42) instance set, so scores are stable;
    # assert a clear margin rather than a brittle exact value.
    assert curve.band > 0.03


def test_state_survives_hard_reset_so_rk_equals_ceiling():
    """The thesis: with a surviving state-dir, a hard reset loses nothing. Each
    non-wiping R(k) arm reloads its accumulated peaks after the SIGKILL, so it
    scores at the ceiling and retains the full band (norm_gain == 1)."""
    curve = _sweep()
    assert curve.points, "expected at least one R(k) point"
    for point in curve.points:
        assert point.k > 0  # hard resets actually fired
        assert point.mean_reward == pytest.approx(curve.ceiling)
        assert point.normalised_gain == pytest.approx(1.0)
        # CL-Bench's own mean_gain reconciles with R(k) - P.
        assert point.clbench_mean_gain == pytest.approx(curve.band)
