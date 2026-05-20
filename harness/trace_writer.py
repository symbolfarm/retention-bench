"""Trace writer: produces the run directory layout per docs/trace-schema.md.

Files written:
  - trace.jsonl          (event stream)
  - questions.jsonl      (per-question records, one per (question, probe))
  - stages/<event_id>.in   (rendered STAGE_INPUT — tagged-section text)
  - stages/<event_id>.out  (raw SUT response — JSON object written by harness)
  - snapshots/reset-<event_id>.tar.gz (handled by dir_lifecycle)
  - run-manifest.json    (harness-side run metadata)
  - sut-manifest.json    (copied from the SUT package; M4 reads it via the CLI)
"""

from __future__ import annotations

import json
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

    def write_stage_output_json(self, event_id: str, reply: dict[str, Any]) -> str:
        """Persist the SUT's parsed JSON reply to stages/<event_id>.out.

        Written as compact JSON (the same line the SUT emitted on stdout, modulo
        whitespace and key ordering). Kept for audit + replay.
        """
        path = self.dirs.stages / f"{event_id}.out"
        path.write_text(
            json.dumps(reply, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8",
        )
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


# ----- SUT answer lookup (per docs/trace-schema.md "SUT-answer ingestion") -----


def lookup_sut_answers(
    answers: list[Any], question_ids: list[str]
) -> dict[str, dict[str, str]]:
    """Build per-question records from the SUT's structured `answers` list.

    The SUT emits something like:
      [{"id":"q1","text":"travelling salesman"}, {"id":"q2","text":"the chief clerk"}]

    Returns {question_id: {"sut_answer": str, "parsing_status": "ok"|"not_found"|"ambiguous"}}
    for each requested question_id.

    No text parsing. Earlier drafts regex-parsed <ANSWER> tags out of a string
    blob; M4 (2026-05-20) flipped this so the harness is genuinely format-agnostic.
    """
    found: dict[str, list[str]] = {}
    for entry in answers:
        if not isinstance(entry, dict):
            continue
        qid = entry.get("id")
        text = entry.get("text", "")
        if qid is None:
            continue
        found.setdefault(str(qid), []).append(str(text))

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
