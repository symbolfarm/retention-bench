"""Trace writer: produces the run directory layout per docs/trace-schema.md.

Files written:
  - trace.jsonl          (event stream)
  - questions.jsonl      (per-question records, one per (question, probe))
  - stages/<event_id>.in / .out (raw stage payloads)
  - snapshots/reset-<event_id>.tar.gz (handled by dir_lifecycle)
  - run-manifest.json    (harness-side run metadata)
  - sut-manifest.json    (copied from SUT; if absent, a stub is written)
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class RunDirs:
    root: Path
    stages: Path
    snapshots: Path

    @classmethod
    def create(cls, root: Path) -> "RunDirs":
        root = root.resolve()
        stages = root / "stages"
        snapshots = root / "snapshots"
        root.mkdir(parents=True, exist_ok=True)
        stages.mkdir(exist_ok=True)
        snapshots.mkdir(exist_ok=True)
        return cls(root=root, stages=stages, snapshots=snapshots)


class TraceWriter:
    """Appends events to trace.jsonl + per-question records to questions.jsonl.

    Stage payloads are written to `stages/<event_id>.{in,out}` and only their
    relative paths land in trace.jsonl.
    """

    def __init__(self, dirs: RunDirs):
        self.dirs = dirs
        self.trace_path = dirs.root / "trace.jsonl"
        self.questions_path = dirs.root / "questions.jsonl"
        self._trace_fh = self.trace_path.open("a", encoding="utf-8")
        self._questions_fh = self.questions_path.open("a", encoding="utf-8")

    def close(self) -> None:
        self._trace_fh.close()
        self._questions_fh.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---- stage payload persistence ----

    def write_stage_input(self, event_id: str, payload: str) -> tuple[str, int]:
        path = self.dirs.stages / f"{event_id}.in"
        data = payload.encode("utf-8")
        path.write_bytes(data)
        return str(path.relative_to(self.dirs.root)), len(data)

    def write_stage_output(self, event_id: str, payload: str) -> str:
        path = self.dirs.stages / f"{event_id}.out"
        path.write_bytes(payload.encode("utf-8"))
        return str(path.relative_to(self.dirs.root))

    # ---- event records ----

    def write_event(self, record: dict[str, Any]) -> None:
        self._trace_fh.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")
        self._trace_fh.flush()

    def write_question_record(self, record: dict[str, Any]) -> None:
        self._questions_fh.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")
        self._questions_fh.flush()

    # ---- manifests ----

    def write_run_manifest(self, manifest: dict[str, Any]) -> None:
        (self.dirs.root / "run-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def write_sut_manifest(self, manifest: dict[str, Any]) -> None:
        (self.dirs.root / "sut-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ----- SUT answer parsing (per docs/trace-schema.md "SUT-answer parsing") -----

_ANSWER_RE = re.compile(
    r"<ANSWER\s+id=\"([^\"]+)\">(.*?)</ANSWER>",
    re.DOTALL,
)


def parse_sut_answers(stage_output: str, question_ids: list[str]) -> dict[str, dict[str, str]]:
    """Parse SUT stage_output for <ANSWER id="..."> tags.

    Returns {question_id: {"sut_answer": str, "parsing_status": "ok"|"not_found"|"ambiguous"}}
    for each question_id requested.
    """
    found: dict[str, list[str]] = {}
    for m in _ANSWER_RE.finditer(stage_output):
        qid, body = m.group(1), m.group(2).strip()
        found.setdefault(qid, []).append(body)

    out: dict[str, dict[str, str]] = {}
    for qid in question_ids:
        hits = found.get(qid, [])
        if not hits:
            out[qid] = {"sut_answer": "", "parsing_status": "not_found"}
        elif len(hits) == 1:
            out[qid] = {"sut_answer": hits[0], "parsing_status": "ok"}
        else:
            out[qid] = {"sut_answer": hits[0], "parsing_status": "ambiguous"}
    return out
