"""The phased store-removal calibration ladder (RB-21).

`--reset-at` asks whether capability migrated into the durable artifact. Until
RB-21 it had one worked example and no ladder, so the protocol was *argued* to
discriminate rather than *demonstrated* to. These tests are that demonstration
in CI: the rungs separate in the expected order, the middle one lands strictly
between, and — the part that matters most — the phased number alone does not
identify consolidation, because a SUT that persists its raw store to the
survive-dir scores the same 1.000 for the wrong reason.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from retention_bench import EveryNInstances  # noqa: E402
from retention_bench._clbench import get_task_class  # noqa: E402
from retention_bench.gain_curve import run_reset_sweep  # noqa: E402
from retention_bench.reset_schedule import ExplicitBoundaries  # noqa: E402
from retention_bench.system import SubprocessSystem  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSOLIDATING_PKG = REPO_ROOT / "suts" / "consolidating_memory"
ASSOCIATIVE_PKG = REPO_ROOT / "suts" / "associative_memory"

# symbolic_associative_retention's default schedule: 48 train instances
# (32 object facts + 16 rules) then 64 probes. The train/probe boundary is 48.
TRAIN_BOUNDARY = 48
FULL_CEILING = 64 / 112


def _sweep(package: Path, module: str, name: str):
    # The SUT inherits the harness environment (harness/sut_process.spawn_sut),
    # so the knobs are set with monkeypatch.setenv by the caller.
    def make_system(state_dir: Path, schedule, wipe: bool) -> SubprocessSystem:
        return SubprocessSystem(
            ["python", "-m", module],
            state_dir,
            reset_schedule=schedule,
            wipe_on_reset=wipe,
            name=name,
            extra_pythonpath=[package],
        )

    return run_reset_sweep(
        make_system,
        lambda: get_task_class("symbolic_associative_retention")(),
        [ExplicitBoundaries([TRAIN_BOUNDARY]), EveryNInstances(1)],
        system_name=name,
        state_root=Path(tempfile.mkdtemp(prefix="rb21-")),
    )


def _arms(curve) -> tuple[float, float]:
    """(phased normalised gain, uniform normalised gain)."""
    by_label = {point.schedule_label: point.normalised_gain for point in curve.points}
    return by_label[f"boundaries:{TRAIN_BOUNDARY}"], by_label["every_1"]


def _consolidating(monkeypatch, fraction: str, name: str, selector: str = "ordinal"):
    monkeypatch.setenv("CONSOLIDATION_FRACTION", fraction)
    monkeypatch.setenv("CONSOLIDATION_SELECTOR", selector)
    return _sweep(CONSOLIDATING_PKG, "consolidating_memory.clbench_main", name)


def test_phased_ladder_rungs_separate_in_order(monkeypatch):
    floor = _consolidating(monkeypatch, "0.0", "consolidate-none")
    partial = _consolidating(monkeypatch, "0.5", "consolidate-partial")
    full = _consolidating(monkeypatch, "1.0", "consolidate-full")

    floor_phased, _ = _arms(floor)
    partial_phased, _ = _arms(partial)
    full_phased, _ = _arms(full)

    assert floor_phased == pytest.approx(0.0)
    assert full_phased == pytest.approx(1.0)
    assert floor_phased < partial_phased < full_phased
    # The migrated fraction, exactly: the ordinal selector lines up with the
    # task's `object i -> attribute i % A` layout, so 2-hop transfer survives at
    # the same rate as 1-hop recall. See the hashed rung for the unaligned case.
    assert partial_phased == pytest.approx(0.5)
    assert full.ceiling == pytest.approx(FULL_CEILING)


def test_hashed_selector_lands_between_without_the_alignment(monkeypatch):
    hashed_phased, _ = _arms(
        _consolidating(monkeypatch, "0.5", "consolidate-hashed", "hashed")
    )
    ordinal_phased, _ = _arms(_consolidating(monkeypatch, "0.5", "consolidate-partial"))
    assert 0.0 < hashed_phased < ordinal_phased
    # Transfer survives at roughly the square of the recall rate once migration
    # is independent per fact, so the same fraction scores visibly lower.
    assert hashed_phased == pytest.approx(0.344, abs=0.01)


def test_batch_consolidation_needs_the_phased_protocol_to_show(monkeypatch):
    """The signature the protocol exists to detect: 1.000 phased, 0.000 uniform."""
    phased, uniform = _arms(_consolidating(monkeypatch, "1.0", "consolidate-full"))
    assert phased == pytest.approx(1.0)
    assert uniform == pytest.approx(0.0)


def test_raw_store_control_scores_the_ceiling_in_both_arms(monkeypatch):
    """The contract violation the protocol cannot see, and the arm that can.

    `associative_memory` persists its raw store to the survive-dir, so the hard
    reset does not remove it and the phased protocol degenerates to the
    store-present condition. Its phased score is indistinguishable from genuine
    consolidation; its uniform score is what gives it away.
    """
    phased, uniform = _arms(
        _sweep(ASSOCIATIVE_PKG, "associative_memory.clbench_main", "raw-store-control")
    )
    consolidator_phased, consolidator_uniform = _arms(
        _consolidating(monkeypatch, "1.0", "consolidate-full")
    )
    assert phased == pytest.approx(consolidator_phased)
    assert uniform == pytest.approx(1.0)
    assert consolidator_uniform == pytest.approx(0.0)
