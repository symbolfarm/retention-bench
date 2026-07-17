"""Deterministic symbolic associative-retention curriculum task."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from retention_bench._clbench import (
    ContinualLearningTask,
    EvalMetrics,
    InstanceOutcome,
    Observation,
    Query,
    Response,
    TaskResult,
    TaskStepResult,
)


class AssociativeAnswer(BaseModel):
    """Minimal exact-scored answer schema."""

    answer: str


Phase = Literal["train", "recall", "transfer"]
Component = Literal["context", "memorization", "transfer"]


@dataclass(frozen=True)
class CurriculumInstance:
    phase: Phase
    component: Component
    concept_id: str
    prompt: str
    expected: str
    exposure_index: int
    probe_after_exposures: int
    scored: bool


class SymbolicAssociativeRetentionTask(ContinualLearningTask):
    """Teach nonce object attributes and attribute-to-bin rules, then probe both."""

    # Class-attribute default: 8 object facts + 2 rules + 16 probes, one exposure.
    # This is the value for the *default* constructor schedule only — it is
    # stale for any other `num_concepts`/`num_exposures` (e.g. `num_exposures=2`
    # doubles the train instances to 20, giving 16/36, not 16/26). Downstream
    # CL-Bench-side tooling that reads the class attribute directly (before an
    # instance exists) still needs a positive default, so it stays here;
    # `build_canonical_run_state` below shadows it with the true per-schedule
    # value as an instance attribute once the concrete schedule is known.
    r_max = 16 / 26

    _OBJECT_NAMES = (
        "norb",
        "tave",
        "luma",
        "zek",
        "pim",
        "dax",
        "vosh",
        "mip",
        "krel",
        "sorn",
        "yav",
        "bex",
    )
    _ATTRIBUTES = ("red", "blue")
    _BINS = ("bin-a", "bin-b")

    def __init__(
        self,
        num_instances: int | None = None,
        *,
        num_concepts: int = 8,
        seed: int = 0,
        num_exposures: int = 1,
        probe_after_exposures: int = 1,
    ):
        if num_concepts < 1:
            raise ValueError("num_concepts must be >= 1")
        if num_concepts > len(self._OBJECT_NAMES):
            raise ValueError(f"num_concepts must be <= {len(self._OBJECT_NAMES)}")
        if num_exposures < 1:
            raise ValueError("num_exposures must be >= 1")
        if probe_after_exposures < 1:
            raise ValueError("probe_after_exposures must be >= 1")
        if seed != 0:
            raise ValueError("Only seed=0 is implemented for the deterministic default schedule")

        self._requested_num_instances = num_instances
        self.num_instances = 0
        self.num_concepts = num_concepts
        self.seed = seed
        self.num_exposures = num_exposures
        self.probe_after_exposures = probe_after_exposures
        self.instances: list[CurriculumInstance] = []
        self._pos = 0
        self._instance_outcomes: list[InstanceOutcome] = []

    def build_canonical_run_state(self) -> None:
        instances = self._build_instances()
        if self._requested_num_instances is not None:
            if self._requested_num_instances < 1:
                raise ValueError("num_instances must be >= 1 when provided")
            if self._requested_num_instances > len(instances):
                raise ValueError(
                    f"num_instances={self._requested_num_instances} exceeds "
                    f"the generated schedule length {len(instances)}"
                )
            instances = instances[: self._requested_num_instances]
        self.instances = instances
        self.num_instances = len(instances)
        self._pos = 0
        self._instance_outcomes = []
        # Per-instance mean maximum reward for *this* concrete schedule: only
        # `scored` (recall/transfer probe) instances can ever score 1.0, and
        # train/context instances always score 0.0. Computed here (not left as
        # the class-attribute default) so `num_exposures`/`num_concepts`/
        # `num_instances` overrides all get the right value instead of the
        # stale 8-concept/1-exposure default.
        num_scored = sum(1 for inst in instances if inst.scored)
        self.r_max = num_scored / len(instances) if instances else 0.0

    def _build_instances(self) -> list[CurriculumInstance]:
        objects = self._OBJECT_NAMES[: self.num_concepts]
        attr_for = {obj: self._ATTRIBUTES[i % len(self._ATTRIBUTES)] for i, obj in enumerate(objects)}
        bin_for = dict(zip(self._ATTRIBUTES, self._BINS))

        instances: list[CurriculumInstance] = []
        for exposure in range(self.num_exposures):
            for obj in objects:
                attr = attr_for[obj]
                instances.append(
                    CurriculumInstance(
                        phase="train",
                        component="context",
                        concept_id=f"object:{obj}",
                        prompt=(
                            "TRAIN object_attribute\n"
                            f"object: {obj}\n"
                            f"attribute: {attr}\n"
                            "Reply exactly: stored"
                        ),
                        expected="stored",
                        exposure_index=exposure,
                        probe_after_exposures=0,
                        scored=False,
                    )
                )
            for attr, bin_name in bin_for.items():
                instances.append(
                    CurriculumInstance(
                        phase="train",
                        component="context",
                        concept_id=f"rule:{attr}",
                        prompt=(
                            "TRAIN attribute_bin_rule\n"
                            f"attribute: {attr}\n"
                            f"bin: {bin_name}\n"
                            "Reply exactly: stored"
                        ),
                        expected="stored",
                        exposure_index=exposure,
                        probe_after_exposures=0,
                        scored=False,
                    )
                )

        for obj in objects:
            attr = attr_for[obj]
            instances.append(
                CurriculumInstance(
                    phase="recall",
                    component="memorization",
                    concept_id=f"object:{obj}",
                    prompt=(
                        "RECALL object_attribute\n"
                        f"object: {obj}\n"
                        "What attribute was taught for this object? Reply with the attribute only."
                    ),
                    expected=attr,
                    exposure_index=self.num_exposures - 1,
                    probe_after_exposures=self.probe_after_exposures,
                    scored=True,
                )
            )
        for obj in objects:
            attr = attr_for[obj]
            instances.append(
                CurriculumInstance(
                    phase="transfer",
                    component="transfer",
                    concept_id=f"object:{obj}",
                    prompt=(
                        "TRANSFER object_bin\n"
                        f"object: {obj}\n"
                        "Using the taught object attribute and attribute-to-bin rule, "
                        "which bin should this object go to? Reply with the bin only."
                    ),
                    expected=bin_for[attr],
                    exposure_index=self.num_exposures - 1,
                    probe_after_exposures=self.probe_after_exposures,
                    scored=True,
                )
            )
        return instances

    def build_current_query(self) -> Query:
        inst = self.instances[self._pos]
        idx = self.canonical_instance_index(self._pos)
        return Query(
            prompt=inst.prompt,
            response_schema=AssociativeAnswer,
            instance_id=f"assoc-{idx:04d}",
            instance_index=idx,
            metadata=self._metadata(inst),
        )

    def step(self, response: Response) -> TaskStepResult:
        inst = self.instances[self._pos]
        idx = self.canonical_instance_index(self._pos)
        got = self._normalize(getattr(response.action, "answer", ""))
        expected = self._normalize(inst.expected)
        reward = 1.0 if inst.scored and got == expected else 0.0
        metadata = self._metadata(inst) | {"got": got, "scored": inst.scored}
        outcome = InstanceOutcome(
            instance_id=f"assoc-{idx:04d}",
            instance_index=idx,
            reward=reward,
            success=(got == expected) if inst.scored else None,
            raw_metric_name="exact_match",
            raw_metric_value=reward,
            raw_metric_higher_is_better=True,
            metadata=metadata,
        )
        self._instance_outcomes.append(outcome)

        self._pos += 1
        done = self._pos >= len(self.instances)
        next_query = None if done else self.build_current_query()
        observation = Observation(
            content=f"expected {expected}, got {got}",
            instance_complete=True,
            metadata=metadata,
        )
        return TaskStepResult(
            observation=observation,
            next_query=next_query,
            done=done,
            instance_outcome=outcome,
        )

    def evaluate(self) -> TaskResult:
        rewards = [o.reward for o in self._instance_outcomes]
        probe_outcomes = [
            o for o in self._instance_outcomes if (o.metadata or {}).get("scored") is True
        ]
        memorization = self._component_outcomes("memorization")
        transfer = self._component_outcomes("transfer")
        metrics = {
            "total_reward": round(sum(rewards), 6),
            "num_instances": len(self._instance_outcomes),
            "num_train_instances": len(self._instance_outcomes) - len(probe_outcomes),
            "num_probe_instances": len(probe_outcomes),
            "probe_mean_reward": self._mean_reward(probe_outcomes),
            "memorization_mean_reward": self._mean_reward(memorization),
            "transfer_mean_reward": self._mean_reward(transfer),
        }
        loss_curve = [round(1.0 - o.reward, 6) if (o.metadata or {}).get("scored") else 0.0 for o in self._instance_outcomes]
        return TaskResult(
            metrics=metrics,
            summary=(
                f"Probe mean reward: {metrics['probe_mean_reward']:.4f} "
                f"over {metrics['num_probe_instances']} probe instance(s). "
                "Whole-run CL-Bench score includes zero-reward train/context instances."
            ),
            eval_metrics=EvalMetrics(
                loss_curve=loss_curve,
                optimal_performance=float(len(probe_outcomes)),
                actual_performance=round(sum(rewards), 6),
                extra={
                    "probe_mean_reward": metrics["probe_mean_reward"],
                    "memorization_mean_reward": metrics["memorization_mean_reward"],
                    "transfer_mean_reward": metrics["transfer_mean_reward"],
                },
            ),
            instance_outcomes=list(self._instance_outcomes),
        )

    def _component_outcomes(self, component: str) -> list[InstanceOutcome]:
        return [
            o
            for o in self._instance_outcomes
            if (o.metadata or {}).get("component") == component
            and (o.metadata or {}).get("scored") is True
        ]

    @staticmethod
    def _mean_reward(outcomes: list[InstanceOutcome]) -> float:
        if not outcomes:
            return 0.0
        return round(float(statistics.mean(o.reward for o in outcomes)), 6)

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value).strip().lower()

    @staticmethod
    def _metadata(inst: CurriculumInstance) -> dict[str, Any]:
        return {
            "phase": inst.phase,
            "component": inst.component,
            "concept_id": inst.concept_id,
            "expected": inst.expected,
            "exposure_index": inst.exposure_index,
            "probe_after_exposures": inst.probe_after_exposures,
        }

    @property
    def name(self) -> str:
        return "symbolic_associative_retention"

    @property
    def description(self) -> str:
        return "Deterministic symbolic associative retention with memorization and transfer probes."
