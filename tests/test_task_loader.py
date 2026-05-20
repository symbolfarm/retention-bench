"""Tests for task_loader schema + semantic validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import task_loader


def _write_task(tmp_path: Path, body: str, materials: dict[str, str] | None = None) -> Path:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "task.yaml").write_text(body, encoding="utf-8")
    for name, content in (materials or {}).items():
        (task_dir / name).write_text(content, encoding="utf-8")
    return task_dir / "task.yaml"


MINIMAL_TASK = """
task_id: t1
schema_version: 1
description: minimal
materials:
  - id: m1
    text: "hello"
questions:
  - id: q1
    text: "what?"
    gold: "yes"
    type: surface_factual
    material_ref: m1
events:
  - type: quiz
    questions: [q1]
    probe: prior
  - type: read
    material_id: m1
  - type: quiz
    questions: [q1]
    probe: ceiling
  - type: reset
  - type: quiz
    questions: [q1]
    probe: retention
    k: 1
"""


def test_loads_well_formed_task(tmp_path: Path) -> None:
    path = _write_task(tmp_path, MINIMAL_TASK)
    td = task_loader.load_task(path)
    assert td.task_id == "t1"
    assert set(td.materials) == {"m1"}
    assert set(td.questions) == {"q1"}
    assert [e.type for e in td.events] == ["quiz", "read", "quiz", "reset", "quiz"]


def test_prior_after_read_rejected(tmp_path: Path) -> None:
    body = MINIMAL_TASK.replace(
        "  - type: quiz\n    questions: [q1]\n    probe: prior\n  - type: read",
        "  - type: read",
    ).replace(
        "  - type: reset\n",
        "  - type: reset\n  - type: quiz\n    questions: [q1]\n    probe: prior\n",
    )
    path = _write_task(tmp_path, body)
    with pytest.raises(task_loader.TaskDefinitionError, match="prior probe"):
        task_loader.load_task(path)


def test_retention_k_mismatch_rejected(tmp_path: Path) -> None:
    body = MINIMAL_TASK.replace("k: 1", "k: 2")
    path = _write_task(tmp_path, body)
    with pytest.raises(task_loader.TaskDefinitionError, match="k=2"):
        task_loader.load_task(path)


def test_unknown_material_ref_rejected(tmp_path: Path) -> None:
    body = MINIMAL_TASK.replace("material_ref: m1", "material_ref: nope")
    path = _write_task(tmp_path, body)
    with pytest.raises(task_loader.TaskDefinitionError, match="unknown material"):
        task_loader.load_task(path)


def test_material_path_or_text_exclusive(tmp_path: Path) -> None:
    body = """
task_id: t1
schema_version: 1
materials:
  - id: m1
    text: hi
    path: also.txt
questions: []
events:
  - type: read
    material_id: m1
"""
    path = _write_task(tmp_path, body, materials={"also.txt": "x"})
    with pytest.raises(task_loader.TaskDefinitionError, match="exactly one of"):
        task_loader.load_task(path)
