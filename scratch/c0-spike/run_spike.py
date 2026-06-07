#!/usr/bin/env python3
"""C0 integration spike: drive a SubprocessSystem through CL-Bench's real runner.

Proves three things with zero changes to CL-Bench core:
  1. Our process-contract SUT can be wrapped as a `ContinualLearningSystem`
     and driven by `src.runtime.runner.run_task` (the adapter seam).
  2. A hard RESET (SIGKILL + respawn, only the on-disk survive-dir persists),
     expressed entirely via the existing `reset_between_instances` hook, retains
     state across resets -> full reward.
  3. The same hook with the survive-dir *wiped* is CL-Bench's stateless
     baseline -> reward collapses. The harness discriminates retention.

Run with the cl-bench 3.13 venv:
    /home/agent/src/cl-bench/.venv/bin/python run_spike.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Reuse retention-bench's process lifecycle (spawn/kill) verbatim — the bit we
# keep from the old harness. This is the "your sut_process IS the SubprocessSystem"
# claim, exercised for real.
sys.path.insert(0, "/workspace")
from harness import sut_process  # noqa: E402

from pydantic import BaseModel  # noqa: E402
from src.interface import (  # noqa: E402
    ContinualLearningSystem,
    ContinualLearningTask,
    InstanceOutcome,
    Observation,
    Query,
    Response,
    TaskResult,
    TaskStepResult,
    standard_evaluate,
)

SUT = str(Path(__file__).resolve().parent / "counter_sut.py")


# --------------------------------------------------------------------------- #
# The adapter: our process contract -> CL-Bench's ContinualLearningSystem.
# --------------------------------------------------------------------------- #
class SubprocessSystem(ContinualLearningSystem):
    def __init__(self, state_dir: Path, *, wipe_on_reset: bool, name: str):
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._wipe_on_reset = wipe_on_reset
        self._name = name
        self._handle = None
        self.spawns = 0
        self.kills = 0

    def _spawn(self) -> None:
        self._handle = sut_process.spawn_sut(
            ["python", SUT],
            dir_path=self._state_dir,
            invocation_index=self.spawns,
            stderr_log=self._state_dir / "sut-stderr.log",
        )
        self.spawns += 1

    def respond(self, query: Query) -> Response:
        if self._handle is None:
            self._spawn()
        req = json.dumps({"prompt": query.prompt}) + "\n"
        self._handle.process.stdin.write(req)
        self._handle.process.stdin.flush()
        line = self._handle.process.stdout.readline()
        reply = json.loads(line)
        action = query.response_schema(**reply)
        return Response(action=action)

    def reset(self) -> None:
        # HARD reset: SIGKILL the process; only the on-disk survive-dir lives on.
        if self._handle is not None:
            sut_process.kill_sut(self._handle)
            self.kills += 1
            self._handle = None
        if self._wipe_on_reset:  # stateless baseline: nothing survives
            for p in self._state_dir.glob("state.json"):
                p.unlink()
        # respawn lazily on next respond()

    @property
    def name(self) -> str:
        return self._name


# --------------------------------------------------------------------------- #
# A minimal single-shot retention task. Each instance asks "how many instances
# have you processed?" — unanswerable without state carried across instances
# (and, under reset_between_instances, across hard resets).
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
            prompt="How many task instances have you processed so far, "
            "including this one? Reply with the integer count.",
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
            raw_metric_name="counter_correct",
            raw_metric_value=float(got),
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


def _run(label: str, *, wipe_on_reset: bool, reset_between_instances: bool) -> TaskResult:
    from src.runtime.runner import run_task

    task = CounterRetentionTask(num_instances=5)
    state_dir = Path(tempfile.mkdtemp(prefix="c0-"))
    system = SubprocessSystem(state_dir, wipe_on_reset=wipe_on_reset, name=label)
    result = run_task(
        task,
        system,
        show_progress=False,
        reset_between_instances=reset_between_instances,
    )
    seq = [(o.metadata["got"], o.metadata["expected"], o.reward) for o in result.instance_outcomes]
    print(f"\n## {label}")
    print(f"   reset_between_instances={reset_between_instances}  wipe_on_reset={wipe_on_reset}")
    print(f"   spawns={system.spawns}  hard_kills={system.kills}")
    print(f"   (got, expected, reward) per instance: {seq}")
    print(f"   SCORE (mean reward) = {result.score:.3f}")
    return result


def main() -> None:
    print("=" * 70)
    print("C0 SPIKE — SubprocessSystem driven by CL-Bench's real runner")
    print("=" * 70)
    stateful = _run("A: stateful, no reset", wipe_on_reset=False, reset_between_instances=False)
    retention = _run("B: HARD RESET + survive-dir (retention)", wipe_on_reset=False, reset_between_instances=True)
    stateless = _run("C: HARD RESET + wipe (stateless baseline)", wipe_on_reset=True, reset_between_instances=True)

    r_max = 1.0
    sl = stateless.score
    norm_gain_retention = (retention.score - sl) / (r_max - sl) if r_max != sl else float("nan")
    print("\n" + "=" * 70)
    print("RESULT")
    print(f"  stateful (no reset)              score = {stateful.score:.3f}")
    print(f"  retention (hard reset + survive) score = {retention.score:.3f}  <- state survived SIGKILLs")
    print(f"  stateless baseline (wiped)       score = {sl:.3f}")
    print(f"  normalized gain of retention vs stateless baseline = {norm_gain_retention:.3f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
