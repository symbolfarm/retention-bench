"""C3: drive the constructive (train-and-grow) SUT through CL-Bench's runner.

This is the headline-contribution path: a *constructive* system (weights mutate,
capacity grows) run as a Continual Learning Bench system via
``retention_bench.SubprocessSystem``, on the C1 target task
(``blind_spectrum_monitoring``), under a hard-reset schedule.

Requires both the ``cl-benchmark`` distribution (import ``src``, Python >=3.13)
*and* ``torch``; the module skips cleanly if either is missing.

What is asserted is the **plumbing**, not task performance — the SUT emits
gibberish by construction (see ``constructive.clbench_main``), so reward gain
over the stateless baseline is uninformative and is deliberately *not* asserted.
The load-bearing claims are:

  * the constructive SUT runs through ``SubprocessSystem`` on the real task and
    returns a ``TaskResult`` (no contract crash);
  * its parametric state lives in the survive-dir and *survives the hard reset*:
    accumulated training (``train_steps``/``read_count``) carries across the
    SIGKILLs in the stateful arm but restarts in the wiped (stateless) arm;
  * capacity is *constructed* mid-run (a growth event grows ``n_layers`` and the
    checkpoint reflects the grown shape, which a fresh post-reset process loads);
  * ``compute`` UsageEvents populate — per-respond FLOPs (the load-bearing cost
    signal) and survive-dir storage deltas (~0 for in-place steps, a jump at the
    growth event).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")
pytest.importorskip("torch", reason="torch not installed")

import torch  # noqa: E402

from retention_bench import EveryNInstances, NoReset, SubprocessSystem  # noqa: E402
from src.interface import Response, TaskResult  # noqa: E402
from src.runtime.runner import run_task  # noqa: E402
from src.tasks.blind_spectrum_monitoring.task import (  # noqa: E402
    BlindSpectrumMonitoringTask,
    ScanReport,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSTRUCTIVE_PKG = REPO_ROOT / "suts" / "constructive"
# "python" is rewritten to sys.executable by spawn_sut; the package is put on the
# subprocess PYTHONPATH via extra_pythonpath so `-m constructive.clbench_main`
# resolves from cwd=survive-dir.
CONSTRUCTIVE_CMD = ["python", "-m", "constructive.clbench_main"]

VARIANT = "five_ch_wide"  # 13 latent channels (5 active + 8 dormant); no corpus needed.
BASE_LAYERS = 1  # tiny test config (see _tiny_model below)


@pytest.fixture(autouse=True)
def _tiny_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tiny model config (via env) so the CPU run is fast. Inherited by the SUT
    subprocess through ``os.environ`` propagation in ``spawn_sut``."""
    monkeypatch.setenv("CONSTRUCTIVE_BLOCK_SIZE", "32")
    monkeypatch.setenv("CONSTRUCTIVE_D_MODEL", "16")
    monkeypatch.setenv("CONSTRUCTIVE_N_HEADS", "2")
    monkeypatch.setenv("CONSTRUCTIVE_N_LAYERS", str(BASE_LAYERS))
    monkeypatch.setenv("CONSTRUCTIVE_SEED", "0")


def _make_system(state_dir: Path, schedule, *, wipe_on_reset: bool = False) -> SubprocessSystem:
    return SubprocessSystem(
        CONSTRUCTIVE_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe_on_reset,
        name="constructive",
        extra_pythonpath=[CONSTRUCTIVE_PKG],
    )


def _run(schedule, *, wipe_on_reset=False, num_instances=6):
    task = BlindSpectrumMonitoringTask(
        variant=VARIANT, num_instances=num_instances, probe_mode=True
    )
    state_dir = Path(tempfile.mkdtemp(prefix="c3-"))
    system = _make_system(state_dir, schedule, wipe_on_reset=wipe_on_reset)
    result = run_task(task, system, show_progress=False, reset_between_instances=False)
    return system, result, state_dir


def _load_meta(state_dir: Path) -> dict:
    blob = torch.load(state_dir / "checkpoint.pt", map_location="cpu", weights_only=False)
    return {"config": blob["config"], "meta": blob["meta"]}


# --------------------------------------------------------------------------- #
# End-to-end through the real runner.
# --------------------------------------------------------------------------- #
def test_constructive_runs_as_clbench_system():
    """Criterion 1: the constructive SUT runs through SubprocessSystem on the
    C1 target task and returns a TaskResult; the SIGKILLs actually happen."""
    system, result, _ = _run(EveryNInstances(2), num_instances=6)
    assert isinstance(result, TaskResult)
    assert 0.0 <= result.score <= 1.0  # a real score; value is gibberish-driven
    # Bounces fire after instances 2 and 4 (the 6th has no next query).
    assert system.scheduled_resets == 2
    assert system.kills == 2
    assert system.spawns == 3  # one initial + one per scheduled reset


def test_capacity_is_constructed_and_survives_reset():
    """Criterion 2 (construction + survival): capacity grows mid-run and the
    grown checkpoint persists across the hard reset.

    A fresh post-reset process must *load* the grown checkpoint (else
    ``load_state_dict`` would mismatch and the run would crash). So a clean run
    through 3 spawns is itself survival evidence; we additionally assert the
    grown shape and a single growth (read_count carried across resets means we
    do not re-grow each segment)."""
    _, _, state_dir = _run(EveryNInstances(2), num_instances=6)
    info = _load_meta(state_dir)
    assert info["config"]["n_layers"] == BASE_LAYERS + 1  # grew exactly once
    assert info["meta"]["growth_count"] == 1
    assert info["meta"]["read_count"] == 6  # all instances seen by one lineage


def test_state_survives_reset_vs_wiped_baseline():
    """Criterion 2 (the retention discriminator): accumulated parametric state
    carries across the SIGKILLs when the survive-dir persists, but restarts when
    it is wiped. Reward can't show this with gibberish output, but the survive-
    dir contents can."""
    _, _, stateful_dir = _run(EveryNInstances(2), num_instances=6)
    _, _, wiped_dir = _run(EveryNInstances(2), wipe_on_reset=True, num_instances=6)

    stateful = _load_meta(stateful_dir)["meta"]
    wiped = _load_meta(wiped_dir)["meta"]

    # Stateful lineage trained on every instance; wiped only on the final segment.
    assert stateful["read_count"] == 6
    assert wiped["read_count"] < stateful["read_count"]
    assert stateful["train_steps"] > wiped["train_steps"]


def test_no_reset_is_single_process_ceiling():
    system, result, state_dir = _run(NoReset(), num_instances=4)
    assert isinstance(result, TaskResult)
    assert system.kills == 0
    assert system.spawns == 1
    assert _load_meta(state_dir)["meta"]["read_count"] == 4


# --------------------------------------------------------------------------- #
# Direct drive: compute UsageEvent accounting (FLOPs + survive-dir storage).
# --------------------------------------------------------------------------- #
def test_respond_emits_compute_event_with_constructive_flops():
    """Criterion 3: per-respond compute events carry SUT-self-reported train
    FLOPs and the constructive resource fields; the action is a valid ScanReport."""
    state_dir = Path(tempfile.mkdtemp(prefix="c3-usage-"))
    system = _make_system(state_dir, NoReset())
    task = BlindSpectrumMonitoringTask(variant=VARIANT, num_instances=3, probe_mode=True)
    task.build_canonical_run_state()
    query = task.build_current_query()

    response = system.respond(query)
    assert isinstance(response.action, ScanReport)  # schema-valid action

    respond_events = [
        e
        for e in system.consume_usage_events()
        if e.call_type == "compute" and e.metadata.get("kind") == "respond"
    ]
    assert len(respond_events) == 1
    ev = respond_events[0]
    assert ev.metadata["flops"] > 0  # bounded gradient step happened
    assert ev.model == "constructive"
    res = ev.metadata["sut_resource"]
    assert res["param_count"] > 0
    assert "growth_count" in res and "n_layers" in res


def test_observe_emits_storage_event_capturing_growth():
    """Criterion 3: the survive-dir storage delta is recorded. The first instance
    grows capacity, so its checkpoint write is a clear positive delta."""
    state_dir = Path(tempfile.mkdtemp(prefix="c3-storage-"))
    system = _make_system(state_dir, EveryNInstances(1))
    task = BlindSpectrumMonitoringTask(variant=VARIANT, num_instances=3, probe_mode=True)
    task.build_canonical_run_state()

    q0 = task.build_current_query()
    response = system.respond(q0)
    step = task.step(response)
    system.observe(step.observation, step.next_query)

    storage = [
        e
        for e in system.consume_usage_events()
        if e.call_type == "compute" and e.metadata.get("kind") == "storage"
    ]
    assert len(storage) == 1
    md = storage[0].metadata
    assert md["survive_dir_bytes"] > 0  # checkpoint.pt written
    assert md["survive_dir_delta_bytes"] > 0  # grown checkpoint from empty dir
    assert md["instance_ordinal"] == 1
    assert md["reset"] is True  # schedule fired (next_query present)
