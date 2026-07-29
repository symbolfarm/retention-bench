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
    held_out: bool = False
    role: str | None = None


class SymbolicAssociativeRetentionTask(ContinualLearningTask):
    """Teach nonce object attributes and attribute-to-bin rules, then probe both.

    Shape (RB-16). With ``num_attributes = A`` and ``objects_per_attribute = n``
    the schedule has ``A * n`` objects; object ``i`` carries attribute
    ``i % A``, and each attribute maps to exactly one bin. The **last ``A``
    objects are held out** — one per attribute, each with ``n - 1`` bridged
    exemplars among the earlier objects. Held-out objects are still *taught*
    (they get their ``TRAIN object_attribute`` instance, so RECALL stays fair
    for them); what they are held out of is **bridging**. Every
    ``TRAIN object_attribute`` prompt carries a ``role: bridge|holdout`` line
    (and the same in query metadata) so a SUT that synthesizes ``object -> bin``
    shortcuts at *write* time can honour the split. Without that split, such a
    SUT turns every TRANSFER probe into a lookup and passes without composing
    anything at query time; **held-out transfer is therefore the composition-
    generalization number**, and ``evaluate()`` reports transfer split by
    bridged vs held-out.

    Default width is ``num_attributes = 16`` (chance ``1/16 = 0.0625`` on both
    probe families, ``0.0357`` as a run-mean) with ``objects_per_attribute = 2``
    → 32 objects, 16 held out. The width matters for validity, not just taste:
    at the pre-RB-16 width of 2 a constant guesser scored 0.5 on both probe
    families (≈0.308 run-mean), which collided exactly with the published
    ``reset_lossy`` rung. See ``suts/random_guess`` for the measured chance rung
    and ``docs/reference-ladder.md``. The width mirrors constructive-retention's
    ``composition_bijection`` (CR-9) so the two repos' held-out transfer numbers
    are comparable; RB deliberately keeps **nonce words** rather than CR's
    single-byte alphabet, because RB's SUTs read prompts as text.

    ``num_attributes=2, objects_per_attribute=4`` reproduces the pre-RB-16
    published schedule (8 objects, 2 rules, 16 probes, ``r_max = 16/26``) so the
    older reference-ladder numbers stay regenerable; the only delta is the added
    ``role:`` line, which no reference SUT reads.
    """

    # Class-attribute default: 32 object facts + 16 rules + 64 probes, one
    # exposure (the default 16-attribute / 2-objects-per-attribute schedule).
    # This is the value for the *default* constructor schedule only — it is
    # stale for any other width/`num_exposures` (e.g. `num_exposures=2` doubles
    # the train instances to 96, giving 64/160, not 64/112). Downstream
    # CL-Bench-side tooling that reads the class attribute directly (before an
    # instance exists) still needs a positive default, so it stays here;
    # `build_canonical_run_state` below shadows it with the true per-schedule
    # value as an instance attribute once the concrete schedule is known.
    r_max = 64 / 112

    # Nonce object names. The first 12 are the pre-RB-16 set, kept in order so
    # narrower schedules (incl. the legacy 8-object one) regenerate exactly.
    _OBJECT_NAMES = (
        "norb", "tave", "luma", "zek", "pim", "dax",
        "vosh", "mip", "krel", "sorn", "yav", "bex",
        "fenu", "quil", "tolm", "grev", "nask", "porl",
        "varn", "huxa", "jeda", "riko", "zubb", "melv",
        "daph", "orlu", "swen", "trix", "vunk", "wemb",
        "xalo", "yint", "zorp", "alek", "brun", "chiv",
        "dremn", "elko", "fasq", "gorv", "hilm", "ivro",
        "jomp", "kesh", "lurn", "morv", "nyle", "obex",
    )
    # Attribute labels. `red`/`blue` head the tuple only so that
    # `num_attributes=2` reproduces the pre-RB-16 schedule byte-for-byte; the
    # rest are nonce words, and nothing about the task depends on an attribute
    # label being meaningful.
    _ATTRIBUTES = (
        "red", "blue", "vint", "korel", "sabo", "quen",
        "thal", "mirek", "oshan", "drivo", "plent", "yura",
        "gemsa", "nuvo", "hastel", "erkin", "cadro", "umbek",
        "zephy", "lodra",
    )
    _BINS = tuple(f"bin-{c}" for c in "abcdefghijklmnopqrst")

    def __init__(
        self,
        num_instances: int | None = None,
        *,
        num_attributes: int = 16,
        objects_per_attribute: int = 2,
        seed: int = 0,
        num_exposures: int = 1,
        probe_after_exposures: int = 1,
    ):
        if num_attributes < 2:
            raise ValueError("num_attributes must be >= 2 (chance level is 1/num_attributes)")
        if num_attributes > len(self._ATTRIBUTES):
            raise ValueError(f"num_attributes must be <= {len(self._ATTRIBUTES)}")
        if objects_per_attribute < 2:
            raise ValueError(
                "objects_per_attribute must be >= 2: one object per attribute is held out "
                "of bridging, so each attribute needs at least one bridged exemplar too"
            )
        num_objects = num_attributes * objects_per_attribute
        if num_objects > len(self._OBJECT_NAMES):
            raise ValueError(
                f"num_attributes * objects_per_attribute = {num_objects} exceeds the "
                f"{len(self._OBJECT_NAMES)} available object names"
            )
        if num_exposures < 1:
            raise ValueError("num_exposures must be >= 1")
        if probe_after_exposures < 1:
            raise ValueError("probe_after_exposures must be >= 1")
        if seed != 0:
            raise ValueError("Only seed=0 is implemented for the deterministic default schedule")

        self._requested_num_instances = num_instances
        self.num_instances = 0
        self.num_attributes = num_attributes
        self.objects_per_attribute = objects_per_attribute
        self.num_objects = num_objects
        # One held-out object per attribute (the last `num_attributes` objects).
        self.num_held_out = num_attributes
        self.chance_level = 1.0 / num_attributes
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
        # the class-attribute default) so `num_exposures`/`num_attributes`/
        # `objects_per_attribute`/`num_instances` overrides all get the right
        # value instead of the stale default-schedule one.
        num_scored = sum(1 for inst in instances if inst.scored)
        self.r_max = num_scored / len(instances) if instances else 0.0

    def _spec(self):
        """Objects, the attribute/bin maps, and the held-out object set."""
        attributes = self._ATTRIBUTES[: self.num_attributes]
        bins = self._BINS[: self.num_attributes]
        objects = self._OBJECT_NAMES[: self.num_objects]
        # Objects cycle through the attributes, so the last `num_attributes`
        # objects are exactly one per attribute — the held-out split.
        attr_for = {obj: attributes[i % self.num_attributes] for i, obj in enumerate(objects)}
        bin_for = dict(zip(attributes, bins))
        held_out = frozenset(objects[self.num_objects - self.num_held_out :])
        return objects, attr_for, bin_for, held_out

    def _build_instances(self) -> list[CurriculumInstance]:
        objects, attr_for, bin_for, held_out = self._spec()

        instances: list[CurriculumInstance] = []
        for exposure in range(self.num_exposures):
            for obj in objects:
                attr = attr_for[obj]
                is_held_out = obj in held_out
                role = "holdout" if is_held_out else "bridge"
                instances.append(
                    CurriculumInstance(
                        phase="train",
                        component="context",
                        concept_id=f"object:{obj}",
                        prompt=(
                            "TRAIN object_attribute\n"
                            f"object: {obj}\n"
                            f"attribute: {attr}\n"
                            f"role: {role}\n"
                            "Reply exactly: stored"
                        ),
                        expected="stored",
                        exposure_index=exposure,
                        probe_after_exposures=0,
                        scored=False,
                        held_out=is_held_out,
                        role=role,
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
                    held_out=obj in held_out,
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
                    held_out=obj in held_out,
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
        transfer_bridged = [o for o in transfer if (o.metadata or {}).get("held_out") is False]
        transfer_heldout = [o for o in transfer if (o.metadata or {}).get("held_out") is True]
        metrics = {
            "total_reward": round(sum(rewards), 6),
            "num_instances": len(self._instance_outcomes),
            "num_train_instances": len(self._instance_outcomes) - len(probe_outcomes),
            "num_probe_instances": len(probe_outcomes),
            "probe_mean_reward": self._mean_reward(probe_outcomes),
            "memorization_mean_reward": self._mean_reward(memorization),
            "transfer_mean_reward": self._mean_reward(transfer),
            # RB-16: transfer split by the bridging held-out set. Held-out
            # transfer is the composition-generalization number — a SUT that
            # synthesizes object->bin shortcuts at write time can only score on
            # it by composing at query time. Chance on both probe families is
            # 1/num_attributes.
            "transfer_bridged_mean_reward": self._mean_reward(transfer_bridged),
            "transfer_heldout_mean_reward": self._mean_reward(transfer_heldout),
            "num_transfer_bridged": len(transfer_bridged),
            "num_transfer_heldout": len(transfer_heldout),
            "chance_level": round(self.chance_level, 6),
        }
        loss_curve = [round(1.0 - o.reward, 6) if (o.metadata or {}).get("scored") else 0.0 for o in self._instance_outcomes]
        return TaskResult(
            metrics=metrics,
            summary=(
                f"Probe mean reward: {metrics['probe_mean_reward']:.4f} "
                f"over {metrics['num_probe_instances']} probe instance(s); "
                f"held-out transfer {metrics['transfer_heldout_mean_reward']:.4f} "
                f"vs bridged {metrics['transfer_bridged_mean_reward']:.4f} "
                f"(chance {metrics['chance_level']:.4f}). "
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
                    "transfer_bridged_mean_reward": metrics["transfer_bridged_mean_reward"],
                    "transfer_heldout_mean_reward": metrics["transfer_heldout_mean_reward"],
                    "chance_level": metrics["chance_level"],
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
        metadata: dict[str, Any] = {
            "phase": inst.phase,
            "component": inst.component,
            "concept_id": inst.concept_id,
            "expected": inst.expected,
            "exposure_index": inst.exposure_index,
            "probe_after_exposures": inst.probe_after_exposures,
            "held_out": inst.held_out,
        }
        if inst.role is not None:
            metadata["role"] = inst.role
        return metadata

    @property
    def name(self) -> str:
        return "symbolic_associative_retention"

    @property
    def description(self) -> str:
        return "Deterministic symbolic associative retention with memorization and transfer probes."
