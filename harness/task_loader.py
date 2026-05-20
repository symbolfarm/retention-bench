"""Load and validate task-definition YAML per docs/task-definition-schema.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


VALID_QUESTION_TYPES = {
    "surface_factual",
    "entity_tracking",
    "multi_hop",
    "thematic",
    "retroactive",
}

VALID_PROBES = {"prior", "ceiling", "retention"}


class TaskDefinitionError(ValueError):
    """Raised when a task definition fails schema or semantic validation."""


@dataclass
class Material:
    id: str
    text: str  # already resolved (inline or read from path)
    source_path: Optional[Path] = None


@dataclass
class Question:
    id: str
    text: str
    gold: str
    type: str
    material_ref: Optional[str]


@dataclass
class Event:
    type: str  # "quiz" | "read" | "reset"
    # quiz fields
    questions: list[str] = field(default_factory=list)
    probe: Optional[str] = None
    k: Optional[int] = None
    # read fields
    material_id: Optional[str] = None


@dataclass
class TaskDefinition:
    task_id: str
    description: str
    schema_version: int
    materials: dict[str, Material]
    questions: dict[str, Question]
    events: list[Event]
    source_path: Path
    event_timeout_seconds: Optional[int] = None  # M4: optional per-task override


def load_task(path: str | Path) -> TaskDefinition:
    """Load a task definition from a YAML file and run schema + semantic validation."""
    p = Path(path).resolve()
    if not p.is_file():
        raise TaskDefinitionError(f"task definition not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise TaskDefinitionError(f"task definition root must be a mapping, got {type(raw).__name__}")

    task_dir = p.parent

    task_id = _require_str(raw, "task_id")
    description = str(raw.get("description", ""))
    schema_version = int(raw.get("schema_version", 1))

    materials = _load_materials(raw.get("materials", []), task_dir)
    questions = _load_questions(raw.get("questions", []))
    events = _load_events(raw.get("events", []))

    event_timeout_seconds: Optional[int] = None
    if "event_timeout_seconds" in raw and raw["event_timeout_seconds"] is not None:
        v = raw["event_timeout_seconds"]
        if not isinstance(v, int) or v <= 0:
            raise TaskDefinitionError(
                f"`event_timeout_seconds` must be a positive integer, got {v!r}"
            )
        event_timeout_seconds = v

    td = TaskDefinition(
        task_id=task_id,
        description=description,
        schema_version=schema_version,
        materials=materials,
        questions=questions,
        events=events,
        source_path=p,
        event_timeout_seconds=event_timeout_seconds,
    )
    _validate_semantics(td)
    return td


def _require_str(d: dict[str, Any], key: str) -> str:
    if key not in d or not isinstance(d[key], str) or not d[key]:
        raise TaskDefinitionError(f"missing or empty required string field: {key!r}")
    return d[key]


def _load_materials(raw_list: Any, task_dir: Path) -> dict[str, Material]:
    if not isinstance(raw_list, list):
        raise TaskDefinitionError("`materials` must be a list")
    out: dict[str, Material] = {}
    for i, m in enumerate(raw_list):
        if not isinstance(m, dict):
            raise TaskDefinitionError(f"materials[{i}] must be a mapping")
        mid = _require_str(m, "id")
        if mid in out:
            raise TaskDefinitionError(f"duplicate material id: {mid!r}")
        has_path = "path" in m and m["path"] is not None
        has_text = "text" in m and m["text"] is not None
        if has_path == has_text:
            raise TaskDefinitionError(
                f"materials[{i}] ({mid!r}) must declare exactly one of `path` or `text`"
            )
        if has_path:
            mat_path = (task_dir / m["path"]).resolve()
            if not mat_path.is_file():
                raise TaskDefinitionError(
                    f"materials[{i}] ({mid!r}) path not found: {mat_path}"
                )
            text = mat_path.read_text(encoding="utf-8")
            out[mid] = Material(id=mid, text=text, source_path=mat_path)
        else:
            out[mid] = Material(id=mid, text=str(m["text"]))
    return out


def _load_questions(raw_list: Any) -> dict[str, Question]:
    if not isinstance(raw_list, list):
        raise TaskDefinitionError("`questions` must be a list")
    out: dict[str, Question] = {}
    for i, q in enumerate(raw_list):
        if not isinstance(q, dict):
            raise TaskDefinitionError(f"questions[{i}] must be a mapping")
        qid = _require_str(q, "id")
        if qid in out:
            raise TaskDefinitionError(f"duplicate question id: {qid!r}")
        text = _require_str(q, "text")
        gold = _require_str(q, "gold")
        qtype = _require_str(q, "type")
        if qtype not in VALID_QUESTION_TYPES:
            raise TaskDefinitionError(
                f"questions[{i}] ({qid!r}) invalid type {qtype!r}; "
                f"must be one of {sorted(VALID_QUESTION_TYPES)}"
            )
        if "material_ref" not in q:
            raise TaskDefinitionError(
                f"questions[{i}] ({qid!r}) missing `material_ref` (use null for pure-prior)"
            )
        material_ref = q["material_ref"]
        if material_ref is not None and not isinstance(material_ref, str):
            raise TaskDefinitionError(
                f"questions[{i}] ({qid!r}) `material_ref` must be a string or null"
            )
        out[qid] = Question(
            id=qid, text=text, gold=gold, type=qtype, material_ref=material_ref
        )
    return out


def _load_events(raw_list: Any) -> list[Event]:
    if not isinstance(raw_list, list) or not raw_list:
        raise TaskDefinitionError("`events` must be a non-empty list")
    out: list[Event] = []
    for i, e in enumerate(raw_list):
        if not isinstance(e, dict):
            raise TaskDefinitionError(f"events[{i}] must be a mapping")
        etype = _require_str(e, "type")
        if etype == "quiz":
            questions = e.get("questions")
            if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
                raise TaskDefinitionError(
                    f"events[{i}] quiz: `questions` must be a list of strings"
                )
            probe = _require_str(e, "probe")
            if probe not in VALID_PROBES:
                raise TaskDefinitionError(
                    f"events[{i}] quiz: invalid probe {probe!r}; must be one of {sorted(VALID_PROBES)}"
                )
            k = e.get("k")
            if probe == "retention":
                if not isinstance(k, int) or k < 1:
                    raise TaskDefinitionError(
                        f"events[{i}] retention quiz requires integer `k` >= 1"
                    )
            elif k is not None:
                raise TaskDefinitionError(
                    f"events[{i}] quiz: `k` is only allowed when probe == 'retention'"
                )
            out.append(Event(type="quiz", questions=list(questions), probe=probe, k=k))
        elif etype == "read":
            material_id = _require_str(e, "material_id")
            out.append(Event(type="read", material_id=material_id))
        elif etype == "reset":
            out.append(Event(type="reset"))
        else:
            raise TaskDefinitionError(
                f"events[{i}] unknown type {etype!r}; must be one of quiz|read|reset"
            )
    return out


def _validate_semantics(td: TaskDefinition) -> None:
    # 1. material refs from READ + questions exist
    for q in td.questions.values():
        if q.material_ref is not None and q.material_ref not in td.materials:
            raise TaskDefinitionError(
                f"question {q.id!r} references unknown material {q.material_ref!r}"
            )
    # 2. quiz question refs exist; read material refs exist
    for i, ev in enumerate(td.events):
        if ev.type == "quiz":
            for qid in ev.questions:
                if qid not in td.questions:
                    raise TaskDefinitionError(
                        f"events[{i}] quiz references unknown question {qid!r}"
                    )
        elif ev.type == "read":
            if ev.material_id not in td.materials:
                raise TaskDefinitionError(
                    f"events[{i}] read references unknown material {ev.material_id!r}"
                )

    # 3/4/5/6. probe ordering. Walk events tracking:
    #   - resets_so_far
    #   - per-material: list of (event_index, resets_at_read) for each READ of that material.
    resets_so_far = 0
    reads_by_material: dict[str, list[tuple[int, int]]] = {}
    for i, ev in enumerate(td.events):
        if ev.type == "read":
            reads_by_material.setdefault(ev.material_id, []).append((i, resets_so_far))
        elif ev.type == "reset":
            resets_so_far += 1
        elif ev.type == "quiz":
            for qid in ev.questions:
                q = td.questions[qid]
                mref = q.material_ref
                reads = reads_by_material.get(mref, []) if mref else []
                if ev.probe == "prior":
                    if mref is not None and reads:
                        raise TaskDefinitionError(
                            f"events[{i}] prior probe of question {qid!r} occurs after a READ of {mref!r}"
                        )
                elif ev.probe == "ceiling":
                    if not reads:
                        raise TaskDefinitionError(
                            f"events[{i}] ceiling probe of question {qid!r} occurs before any READ of {mref!r}"
                        )
                    _, resets_at_read = reads[-1]
                    if resets_so_far != resets_at_read:
                        raise TaskDefinitionError(
                            f"events[{i}] ceiling probe of question {qid!r} crosses a RESET "
                            f"after the READ of {mref!r}"
                        )
                elif ev.probe == "retention":
                    if not reads:
                        raise TaskDefinitionError(
                            f"events[{i}] retention probe of question {qid!r} occurs before any READ of {mref!r}"
                        )
                    if resets_so_far == 0:
                        raise TaskDefinitionError(
                            f"events[{i}] retention probe of question {qid!r} occurs before any RESET"
                        )
                    _, resets_at_read = reads[-1]
                    actual_k = resets_so_far - resets_at_read
                    if actual_k != ev.k:
                        raise TaskDefinitionError(
                            f"events[{i}] retention probe of question {qid!r} declares k={ev.k} "
                            f"but actual RESETs since last READ of {mref!r} is {actual_k}"
                        )
