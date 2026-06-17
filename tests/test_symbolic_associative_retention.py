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
    assert len(a) == 26
    assert [row["metadata"]["phase"] for row in a[:10]] == ["train"] * 10
    assert {row["metadata"]["component"] for row in a[10:18]} == {"memorization"}
    assert {row["metadata"]["component"] for row in a[18:]} == {"transfer"}


def test_response_schema_requires_answer_field():
    task = SymbolicAssociativeRetentionTask(num_concepts=1)
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
    assert result.metrics["num_train_instances"] == 10
    assert result.metrics["num_probe_instances"] == 16
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

    task = SymbolicAssociativeRetentionTask(num_concepts=1, num_instances=4)
    q = task.reset()
    # First three instances are train/context, final instance is recall.
    for _ in range(3):
        step = task.step(Response(action=AssociativeAnswer(answer="stored")))
        q = step.next_query
    assert q.metadata["phase"] == "recall"

    step = task.step(Response(action=EmptyAction()))
    assert step.done
    result = task.evaluate()
    assert result.metrics["memorization_mean_reward"] == pytest.approx(0.0)
