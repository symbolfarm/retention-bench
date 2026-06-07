"""C4: the reset-axis gain curve + reconciliation with CL-Bench's gain.

Drives the deterministic counter SUT (``tests/clbench_assets/counter_sut.py``,
reused from C2) through :func:`retention_bench.run_reset_sweep`. The counter is a
*perfect-retention* SUT — it re-reads its count from the survive-dir on every
request, so a hard reset that keeps the survive-dir is transparent. That makes
the curve deterministic and the reconciliation exact, unlike the constructive
SUT whose rewards are gibberish-noise (see ``.tasks/debriefs/C3.md``).

The load-bearing assertion is the reconciliation: every point's
``clbench_mean_gain`` (computed by CL-Bench's own ``build_benchmark_aggregate``
on per-instance, instance-id-matched outcomes) equals our ``R(k) − P``
numerator (a difference of run-mean rewards).

Requires the ``cl-benchmark`` distribution (import ``src``, Python >=3.13);
skips cleanly otherwise.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from retention_bench import (  # noqa: E402
    EveryNInstances,
    ExplicitBoundaries,
    NoReset,
    ResetSchedule,
    SubprocessSystem,
    run_reset_sweep,
)
from retention_bench.gain_curve import render_curve  # noqa: E402

# Reuse the C2 counter task + SUT command rather than redefine them.
from tests.test_subprocess_system import COUNTER_CMD, CounterRetentionTask  # noqa: E402


def _make_system_factory():
    def make_system(state_dir: Path, schedule: ResetSchedule, wipe: bool) -> SubprocessSystem:
        return SubprocessSystem(
            COUNTER_CMD, state_dir, reset_schedule=schedule, wipe_on_reset=wipe, name="counter"
        )

    return make_system


def _sweep(schedules, *, num_instances=5, epsilon=0.05):
    make_task = lambda: CounterRetentionTask(num_instances=num_instances)  # noqa: E731
    return run_reset_sweep(
        _make_system_factory(),
        make_task,
        schedules,
        system_name="counter",
        state_root=Path(tempfile.mkdtemp(prefix="c4-")),
        epsilon=epsilon,
    )


def test_band_is_fixed_by_ceiling_and_prior():
    """C (no-reset) = 1.0, P (wiped stateless baseline) = 1/N → a learnable band."""
    curve = _sweep([EveryNInstances(1)], num_instances=5)
    assert curve.ceiling == pytest.approx(1.0)
    assert curve.prior == pytest.approx(0.2)  # only the first instance is answerable stateless
    assert curve.band == pytest.approx(0.8)
    assert not curve.excluded


def test_k_axis_is_the_measured_hard_reset_count():
    """k on the curve is the resets the run actually executed, not the nominal
    schedule density. Points are sorted by k."""
    curve = _sweep([EveryNInstances(1), EveryNInstances(2), NoReset()], num_instances=5)
    ks = [p.k for p in curve.points]
    assert ks == sorted(ks)
    # NoReset → 0; every-2 over 5 instances → resets after ordinals 2,4 → 2;
    # every-1 → after ordinals 1..4 → 4.
    assert ks == [0, 2, 4]


def test_perfect_retention_curve_is_flat_at_ceiling():
    """The counter survives every (non-wiping) hard reset, so R(k) stays at the
    ceiling and normalised gain is 1.0 across the whole k-axis."""
    curve = _sweep([EveryNInstances(1), EveryNInstances(2)], num_instances=5)
    for p in curve.points:
        assert p.mean_reward == pytest.approx(1.0)
        assert p.normalised_gain == pytest.approx(1.0)


def test_reconciles_with_clbench_mean_gain():
    """Headline reconciliation: each point's CL-Bench mean_gain equals our
    R(k) − P numerator, and norm_gain × band recovers that gain."""
    curve = _sweep([EveryNInstances(1), EveryNInstances(2), NoReset()], num_instances=5)
    for p in curve.points:
        ours = p.mean_reward - curve.prior  # R(k) − P
        assert p.clbench_mean_gain == pytest.approx(ours, abs=1e-6)
        assert p.normalised_gain * curve.band == pytest.approx(p.clbench_mean_gain, abs=1e-6)


def test_excluded_band_yields_none_normalised_gain():
    """With one instance, the stateless baseline already answers it (count=1,
    expected=1), so C = P = 1.0: no learnable band → curve excluded, points
    report None for normalised gain (mirrors the scorer's C≈P exclusion)."""
    curve = _sweep([EveryNInstances(1)], num_instances=1)
    assert curve.band == pytest.approx(0.0)
    assert curve.excluded
    assert all(p.normalised_gain is None for p in curve.points)
    # The CL-Bench gain numerator is still well-defined (and ~0 here).
    assert all(p.clbench_mean_gain == pytest.approx(0.0, abs=1e-6) for p in curve.points)


def test_explicit_boundaries_arm_measures_placed_resets():
    """C10: an ExplicitBoundaries arm — the tool for placing resets on vs off a
    drift boundary — fires only at the listed ordinals, so measured k equals the
    count of listed ordinals that fall within the run. Boundaries past the run
    length are harmless (never fire)."""
    # 5 instances; resets placed after ordinals 2 and 4 fire (k=2); the 7 never does.
    curve = _sweep([ExplicitBoundaries([2, 4, 7])], num_instances=5)
    (point,) = curve.points
    assert point.k == 2
    assert point.schedule_label == "boundaries:2,4,7"


def test_explicit_boundaries_placement_changes_measured_k():
    """Two placements with different in-range ordinal counts yield different k —
    the axis distinguishes where the resets land, which is what the on-vs-off-drift
    sweep exploits."""
    curve = _sweep(
        [ExplicitBoundaries([2, 4]), ExplicitBoundaries([3])], num_instances=5
    )
    ks = sorted(p.k for p in curve.points)
    assert ks == [1, 2]


def test_cli_reset_at_builds_explicit_boundary_arms():
    """The --reset-at CLI flag parses comma-separated ordinals into one
    ExplicitBoundaries arm each (the surface the drift-placement run uses)."""
    from retention_bench import gain_curve as gc

    captured: dict = {}

    def fake_sweep(make_system, make_task, schedules, **kwargs):
        captured["schedules"] = schedules
        captured["kwargs"] = kwargs
        return _sweep([NoReset()], num_instances=1)  # cheap real GainCurve to render

    monkey = pytest.MonkeyPatch()
    monkey.setattr(gc, "run_reset_sweep", fake_sweep)
    try:
        rc = gc.main(
            [
                "--task", "blind_spectrum_monitoring",
                "--sut", "python -m noop",
                "--reset-at", "30,60",
                "--reset-at", "35,65",
            ]
        )
    finally:
        monkey.undo()

    assert rc == 0
    labels = [s.label for s in captured["schedules"]]
    assert labels == ["boundaries:30,60", "boundaries:35,65"]


def test_render_table_contains_band_and_rows(capsys):
    curve = _sweep([EveryNInstances(1), EveryNInstances(2)], num_instances=5)
    table = render_curve(curve)
    print(table)  # visible under `pytest -s` for eyeballing
    assert "Reset-axis retention curve" in table
    assert "prior" in table and "ceiling" in table and "band" in table
    assert "norm_gain" in table and "clbench_gain" in table
    for p in curve.points:
        assert f"{p.k:>3}" in table
