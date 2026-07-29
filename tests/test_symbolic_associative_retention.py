"""RB-2b: deterministic symbolic associative-retention curriculum task."""

from __future__ import annotations

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from pydantic import BaseModel, ValidationError  # noqa: E402

from retention_bench._clbench import get_task_class, list_tasks  # noqa: E402
from retention_bench.tasks.symbolic_associative_retention import (  # noqa: E402
    AssociativeAnswer,
    SymbolicAssociativeRetentionTask,
)
from src.interface import Response  # noqa: E402


def _queries(task: SymbolicAssociativeRetentionTask):
    q = task.reset()
    out = []
    while True:
        out.append(
            {
                "prompt": q.prompt,
                "instance_id": q.instance_id,
                "instance_index": q.instance_index,
                "metadata": dict(q.metadata or {}),
            }
        )
        answer = q.metadata["expected"] if q.metadata["phase"] != "train" else "stored"
        step = task.step(Response(action=AssociativeAnswer(answer=answer)))
        if step.done:
            break
        q = step.next_query
    return out


def _drive(task: SymbolicAssociativeRetentionTask, answer_for):
    q = task.reset()
    while True:
        answer = answer_for(q)
        step = task.step(Response(action=AssociativeAnswer(answer=answer)))
        if step.done:
            return task.evaluate()
        q = step.next_query


def test_r_max_is_computed_per_instance_schedule_not_stale_class_default():
    """The class attribute (64/112) is only correct for the default 16-attribute,
    2-objects-per-attribute, 1-exposure schedule. `num_exposures=2` doubles the
    train instances to 96 (64/160), so `r_max` must be recomputed per schedule on
    the instance, not left at the stale class-attribute value (2026-07 review
    finding)."""
    default_task = SymbolicAssociativeRetentionTask()
    default_task.reset()
    assert default_task.r_max == pytest.approx(64 / 112)
    assert default_task.r_max == pytest.approx(SymbolicAssociativeRetentionTask.r_max)

    two_exposure_task = SymbolicAssociativeRetentionTask(num_exposures=2)
    two_exposure_task.reset()
    assert two_exposure_task.r_max == pytest.approx(64 / 160)
    # The stale class attribute must be untouched by the instance override.
    assert SymbolicAssociativeRetentionTask.r_max == pytest.approx(64 / 112)


def test_legacy_two_attribute_schedule_is_reproducible():
    """RB-16 widened the default, but the pre-RB-16 schedule (and therefore the
    ladder numbers published against it) must stay regenerable: 2 attributes x 4
    objects = 8 objects, 2 rules, 16 probes, r_max = 16/26. The only intended
    delta is the added `role:` line on TRAIN object_attribute prompts."""
    task = SymbolicAssociativeRetentionTask(num_attributes=2, objects_per_attribute=4)
    task.reset()
    assert task.num_instances == 26
    assert task.r_max == pytest.approx(16 / 26)
    assert task.num_objects == 8
    rows = _queries(task)
    assert [row["metadata"]["expected"] for row in rows[10:]] == (
        ["red", "blue"] * 4 + ["bin-a", "bin-b"] * 4
    )
    assert rows[0]["prompt"] == (
        "TRAIN object_attribute\nobject: norb\nattribute: red\n"
        "role: bridge\nReply exactly: stored"
    )
    assert rows[18]["prompt"] == (
        "TRANSFER object_bin\nobject: norb\n"
        "Using the taught object attribute and attribute-to-bin rule, "
        "which bin should this object go to? Reply with the bin only."
    )


def test_default_width_puts_chance_well_below_the_graded_rung():
    """The RB-16 correctness bug: at 2 attributes both probe families were
    two-way choices, so a constant guesser scored 0.5 probe-mean (0.308
    run-mean) — colliding with reset_lossy's published R(k=12). The default
    width must keep chance far below any retention rung."""
    task = SymbolicAssociativeRetentionTask()
    task.reset()
    assert task.num_attributes == 16
    assert task.chance_level == pytest.approx(1 / 16)
    assert task.chance_level * task.r_max == pytest.approx(0.0357142857, abs=1e-6)


def test_each_attribute_has_a_bridged_and_a_held_out_object():
    task = SymbolicAssociativeRetentionTask()
    task.reset()
    trains = [i for i in task.instances if i.concept_id.startswith("object:") and not i.scored]
    assert len(trains) == 32
    by_role: dict[str, set[str]] = {"bridge": set(), "holdout": set()}
    attr_of = {}
    for inst in trains:
        attr = inst.prompt.splitlines()[2].split(": ", 1)[1]
        by_role[inst.role].add(attr)
        attr_of.setdefault(inst.concept_id, attr)
        # Held-out objects are held out of *bridging*, not of teaching: they
        # still get their TRAIN object_attribute instance.
        assert f"role: {inst.role}" in inst.prompt
    assert len(by_role["holdout"]) == 16
    assert by_role["bridge"] == by_role["holdout"]  # every attribute has both

    # Held-out objects are the last `num_attributes` objects, one per attribute.
    held_out_recalls = [
        i for i in task.instances if i.phase == "recall" and i.held_out
    ]
    assert len(held_out_recalls) == 16
    assert len({i.expected for i in held_out_recalls}) == 16


def test_transfer_is_reported_split_by_bridged_and_held_out():
    """Held-out transfer is the composition-generalization number: score every
    bridged transfer right and every held-out transfer wrong, and the split must
    show it even though the pooled transfer mean is only halved."""

    def answer_for(q):
        md = q.metadata
        if md["phase"] == "train":
            return "stored"
        if md["phase"] == "transfer" and md["held_out"]:
            return "wrong-bin"
        return md["expected"]

    result = _drive(SymbolicAssociativeRetentionTask(), answer_for)

    assert result.metrics["memorization_mean_reward"] == pytest.approx(1.0)
    assert result.metrics["transfer_mean_reward"] == pytest.approx(0.5)
    assert result.metrics["transfer_bridged_mean_reward"] == pytest.approx(1.0)
    assert result.metrics["transfer_heldout_mean_reward"] == pytest.approx(0.0)
    assert result.metrics["num_transfer_bridged"] == 16
    assert result.metrics["num_transfer_heldout"] == 16
    assert result.metrics["chance_level"] == pytest.approx(1 / 16)
    assert "held-out transfer" in result.summary


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_attributes": 1},
        {"num_attributes": 21},
        # Every attribute needs a bridged exemplar as well as a held-out object.
        {"objects_per_attribute": 1},
        # 16 x 4 = 64 objects, more than the available nonce names.
        {"objects_per_attribute": 4},
    ],
)
def test_invalid_widths_are_rejected(kwargs):
    with pytest.raises(ValueError):
        SymbolicAssociativeRetentionTask(**kwargs)


def test_local_task_registry_resolves_symbolic_associative_retention():
    assert "symbolic_associative_retention" in list_tasks()
    assert get_task_class("symbolic_associative_retention") is SymbolicAssociativeRetentionTask


def test_gain_curve_list_tasks_includes_local_task(capsys):
    from retention_bench import gain_curve

    assert gain_curve.main(["--list-tasks"]) == 0
    listed = capsys.readouterr().out.splitlines()
    assert "symbolic_associative_retention" in listed


def test_task_sequence_is_deterministic():
    a = _queries(SymbolicAssociativeRetentionTask())
    b = _queries(SymbolicAssociativeRetentionTask())
    assert a == b
    assert len(a) == 112
    assert [row["metadata"]["phase"] for row in a[:48]] == ["train"] * 48
    assert {row["metadata"]["component"] for row in a[48:80]} == {"memorization"}
    assert {row["metadata"]["component"] for row in a[80:]} == {"transfer"}


def test_response_schema_requires_answer_field():
    task = SymbolicAssociativeRetentionTask(num_attributes=2, objects_per_attribute=2)
    query = task.reset()
    assert query.response_schema is AssociativeAnswer
    with pytest.raises(ValidationError):
        query.response_schema.model_validate({})


def test_exact_scoring_and_component_metrics_all_correct():
    result = _drive(
        SymbolicAssociativeRetentionTask(),
        lambda q: q.metadata["expected"] if q.metadata["phase"] != "train" else "stored",
    )

    assert result.score == pytest.approx(SymbolicAssociativeRetentionTask.r_max)
    assert result.metrics["num_train_instances"] == 48
    assert result.metrics["num_probe_instances"] == 64
    assert result.metrics["probe_mean_reward"] == pytest.approx(1.0)
    assert result.metrics["memorization_mean_reward"] == pytest.approx(1.0)
    assert result.metrics["transfer_mean_reward"] == pytest.approx(1.0)
    assert "zero-reward train/context" in result.summary


def test_transfer_metric_separates_from_memorization_metric():
    def answer_for(q):
        phase = q.metadata["phase"]
        if phase == "train":
            return "stored"
        if phase == "recall":
            return q.metadata["expected"]
        return "wrong-bin"

    result = _drive(SymbolicAssociativeRetentionTask(), answer_for)

    assert result.metrics["memorization_mean_reward"] == pytest.approx(1.0)
    assert result.metrics["transfer_mean_reward"] == pytest.approx(0.0)
    assert result.metrics["probe_mean_reward"] == pytest.approx(0.5)


def test_invalid_action_shape_scores_as_incorrect_not_crash():
    class EmptyAction(BaseModel):
        pass

    task = SymbolicAssociativeRetentionTask(
        num_attributes=2, objects_per_attribute=2, num_instances=7
    )
    q = task.reset()
    # First six instances are train/context (4 objects + 2 rules), 7th is recall.
    for _ in range(6):
        step = task.step(Response(action=AssociativeAnswer(answer="stored")))
        q = step.next_query
    assert q.metadata["phase"] == "recall"

    step = task.step(Response(action=EmptyAction()))
    assert step.done
    result = task.evaluate()
    assert result.metrics["memorization_mean_reward"] == pytest.approx(0.0)
