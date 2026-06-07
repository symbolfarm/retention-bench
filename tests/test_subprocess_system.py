"""C2: drive the production SubprocessSystem through CL-Bench's real runner.

These tests require the ``cl-benchmark`` distribution (import path ``src``,
Python >=3.13). On an interpreter without it (e.g. the legacy 3.12 venv) the
whole module is skipped via ``importorskip`` — it does not fail the suite.

Two layers of assertion:
  * end-to-end through ``src.runtime.runner.run_task`` — score, hard-kill count
    against the schedule, and survive-dir persistence vs wipe; and
  * direct unit drive of ``respond()``/``observe()`` — that ``compute``
    UsageEvents carry SUT-self-reported FLOPs and survive-dir storage deltas.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from pydantic import BaseModel  # noqa: E402

from retention_bench import (  # noqa: E402
    EveryNInstances,
    ExplicitBoundaries,
    NoReset,
    SubprocessSystem,
)
from src.interface import (  # noqa: E402
    ContinualLearningTask,
    InstanceOutcome,
    Observation,
    Query,
    Response,
    TaskResult,
    TaskStepResult,
    standard_evaluate,
)
from src.runtime.runner import run_task  # noqa: E402

_COUNTER_SUT = str(Path(__file__).parent / "clbench_assets" / "counter_sut.py")
COUNTER_CMD = ["python", _COUNTER_SUT]  # "python" is rewritten to sys.executable by spawn_sut


# --------------------------------------------------------------------------- #
# A minimal single-shot retention task: instance i must report ordinal i+1.
# Answerable only if the count survives across instances (and hard resets).
# --------------------------------------------------------------------------- #
class CounterResponse(BaseModel):
    count: int


class CounterRetentionTask(ContinualLearningTask):
    r_max = 1.0

    def __init__(self, num_instances: int = 5):
        self.num_instances = num_instances
        self.instances: list[dict] = []
        self._pos = 0
        self._instance_outcomes: list[InstanceOutcome] = []

    def build_canonical_run_state(self) -> None:
        self.instances = [{"i": i} for i in range(self.num_instances)]
        self._pos = 0
        self._instance_outcomes = []

    def build_current_query(self) -> Query:
        idx = self.canonical_instance_index(self._pos)
        return Query(
            prompt="How many instances have you processed, including this one?",
            response_schema=CounterResponse,
            instance_id=f"inst-{idx}",
            instance_index=idx,
        )

    def step(self, response: Response) -> TaskStepResult:
        expected = self._pos + 1
        got = int(response.action.count)
        reward = 1.0 if got == expected else 0.0
        idx = self.canonical_instance_index(self._pos)
        outcome = InstanceOutcome(
            instance_id=f"inst-{idx}",
            instance_index=idx,
            reward=reward,
            success=(reward == 1.0),
            metadata={"expected": expected, "got": got},
        )
        self._instance_outcomes.append(outcome)
        self._pos += 1
        done = self._pos >= len(self.instances)
        obs = Observation(content=f"expected {expected}, got {got}", instance_complete=True)
        next_q = None if done else self.build_current_query()
        return TaskStepResult(observation=obs, next_query=next_q, done=done, instance_outcome=outcome)

    def evaluate(self) -> TaskResult:
        return standard_evaluate(self._instance_outcomes, optimal_per_instance=1.0)

    @property
    def name(self) -> str:
        return "counter_retention"


def _run(schedule, *, wipe_on_reset=False, num_instances=5):
    task = CounterRetentionTask(num_instances=num_instances)
    state_dir = Path(tempfile.mkdtemp(prefix="c2-test-"))
    system = SubprocessSystem(
        COUNTER_CMD,
        state_dir,
        reset_schedule=schedule,
        wipe_on_reset=wipe_on_reset,
        name="counter",
    )
    result = run_task(task, system, show_progress=False, reset_between_instances=False)
    return system, result


# --------------------------------------------------------------------------- #
# End-to-end through the real runner.
# --------------------------------------------------------------------------- #
def test_no_reset_is_the_stateful_ceiling():
    system, result = _run(NoReset())
    assert result.score == pytest.approx(1.0)
    assert system.kills == 0
    assert system.scheduled_resets == 0
    assert system.spawns == 1  # one process for the whole run


def test_every_instance_reset_retains_via_survive_dir():
    # k=1 density, system-side. State survives every SIGKILL on disk → still 1.0.
    system, result = _run(EveryNInstances(1), num_instances=5)
    assert result.score == pytest.approx(1.0)
    # Bounce fires after instances 1..4; the 5th has no next query → no bounce.
    assert system.scheduled_resets == 4
    assert system.kills == 4


def test_wipe_on_reset_is_the_stateless_baseline():
    # Same k=1 schedule, but the survive-dir is wiped each reset → count restarts.
    # Only the first instance can be correct → score 1/5.
    system, result = _run(EveryNInstances(1), wipe_on_reset=True, num_instances=5)
    assert result.score == pytest.approx(0.2)
    assert system.kills == 4


def test_explicit_boundaries_reset_only_at_listed_ordinals():
    system, result = _run(ExplicitBoundaries({2, 4}), num_instances=5)
    assert result.score == pytest.approx(1.0)  # persisted → still correct
    assert system.scheduled_resets == 2
    assert system.kills == 2


def test_retention_gain_is_discriminated():
    # The framework's mean_gain story: stateful/retention beats stateless.
    _, retention = _run(EveryNInstances(1), wipe_on_reset=False)
    _, stateless = _run(EveryNInstances(1), wipe_on_reset=True)
    assert retention.score > stateless.score


# --------------------------------------------------------------------------- #
# Direct drive: compute UsageEvent accounting (FLOPs + survive-dir storage).
# --------------------------------------------------------------------------- #
def test_respond_emits_compute_event_with_sut_flops():
    state_dir = Path(tempfile.mkdtemp(prefix="c2-usage-"))
    system = SubprocessSystem(COUNTER_CMD, state_dir, name="counter")
    task = CounterRetentionTask(num_instances=3)
    task.build_canonical_run_state()
    query = task.build_current_query()

    response = system.respond(query)
    assert response.action.count == 1

    events = system.consume_usage_events()
    compute = [e for e in events if e.call_type == "compute" and e.metadata.get("kind") == "respond"]
    assert len(compute) == 1
    ev = compute[0]
    assert ev.metadata["flops"] == 1000  # 1000 * count(=1), straight from SUT self-report
    assert ev.input_tokens == 5 and ev.output_tokens == 1
    assert ev.model == "counter-sut"


def test_observe_emits_storage_event_and_tracks_delta():
    state_dir = Path(tempfile.mkdtemp(prefix="c2-storage-"))
    system = SubprocessSystem(COUNTER_CMD, state_dir, reset_schedule=EveryNInstances(1), name="counter")
    task = CounterRetentionTask(num_instances=3)
    task.build_canonical_run_state()

    q0 = task.build_current_query()
    system.respond(q0)
    step = task.step(Response(action=CounterResponse(count=1)))
    system.observe(step.observation, step.next_query)

    storage = [
        e
        for e in system.consume_usage_events()
        if e.call_type == "compute" and e.metadata.get("kind") == "storage"
    ]
    assert len(storage) == 1
    md = storage[0].metadata
    assert md["survive_dir_bytes"] > 0  # state.json was written
    assert md["survive_dir_delta_bytes"] == md["survive_dir_bytes"]  # first measurement
    assert md["reset"] is True  # schedule fired (next_query present)
    assert md["instance_ordinal"] == 1
    assert system.kills == 1
