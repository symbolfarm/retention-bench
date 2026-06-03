"""Scorer entry point: ``python -m scorer <run-dir>``.

Reads ``<run-dir>/questions.jsonl`` (the per-question records file from the
M2/M4 harness — see ``docs/trace-schema.md``), scores each record with the
configured scorer, aggregates per-question, and prints the retention table
to stdout.

Scorer modes
------------
``--scorer exact-match`` (default)
    Uses the exact-match scorer for all question types.  Reproduces M6
    behavior exactly; past smoke runs re-score identically under this mode.

``--scorer judge``
    Routes judge-eligible question types (``entity_tracking``,
    ``multi_hop``) to the LLM judge (OpenAI-compatible API).  ``surface_factual``
    questions still use exact-match regardless of this flag.

    Requires ``OPENROUTER_API_KEY`` in the environment.  Judge rationales are
    written to a sibling ``scoring.jsonl`` file in the run directory.  Judge
    token usage is written to a sibling ``judge_resource_appendix.jsonl``.

Note: the M6 task brief originally specified ``<run-dir>/trace.jsonl`` as
the argument. That predates the M1 file-split decision (``trace.jsonl`` is
the event stream; ``questions.jsonl`` is the scoring contract). We take a
run directory here and open ``questions.jsonl`` internally — see
``.tasks/debriefs/M6.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator

from scorer.aggregate import EPSILON, aggregate_records
from scorer.curve import render_curve


def _load_records(questions_path: Path) -> Iterator[dict]:
    with questions_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(
                    f"{questions_path}: line {line_no}: invalid JSON: {e}"
                )


def _write_judge_resource_appendix(run_dir: Path, appendix: dict) -> None:
    """Write the accumulated judge spend to ``judge_resource_appendix.jsonl``.

    A single aggregate record (one JSONL line), kept separate from the SUT's
    ``resource_appendix`` so scoring spend never contaminates the SUT budget
    (decision #6 open-Q6).
    """
    path = run_dir / "judge_resource_appendix.jsonl"
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(appendix, ensure_ascii=False) + "\n")


def _write_scoring_jsonl(run_dir: Path, scored_records: list[dict]) -> None:
    """Write judge rationales to ``scoring.jsonl`` keyed by ``record_id``."""
    path = run_dir / "scoring.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in scored_records:
            if "judge_rationale" not in rec:
                continue
            entry = {
                "record_id": rec.get("record_id"),
                "question_id": rec.get("question_id"),
                "probe_type": rec.get("probe_type"),
                "scorer_kind": rec.get("scorer_kind"),
                "score": rec.get("score"),
                "judge_rationale": rec["judge_rationale"],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scorer",
        description="Score a retention-bench run directory and print the retention curve.",
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Path to a run directory containing questions.jsonl.",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=EPSILON,
        help=f"ε floor for the C−P exclusion rule (default: {EPSILON}).",
    )
    parser.add_argument(
        "--scorer",
        choices=["exact-match", "judge"],
        default="exact-match",
        help=(
            "Scoring mode. 'exact-match' (default) reproduces M6 behavior. "
            "'judge' routes entity_tracking and multi_hop questions to the "
            "LLM judge (requires OPENROUTER_API_KEY)."
        ),
    )
    args = parser.parse_args(argv)

    run_dir: Path = args.run_dir
    if not run_dir.is_dir():
        print(f"error: not a directory: {run_dir}", file=sys.stderr)
        return 2
    questions_path = run_dir / "questions.jsonl"
    if not questions_path.is_file():
        print(f"error: missing questions.jsonl in {run_dir}", file=sys.stderr)
        return 2

    records = list(_load_records(questions_path))
    scored_records, per_question = aggregate_records(records, scorer_mode=args.scorer)

    # Write scoring.jsonl + judge_resource_appendix.jsonl siblings when running
    # in judge mode (the latter only if the judge was actually engaged).
    if args.scorer == "judge":
        _write_scoring_jsonl(run_dir, scored_records)
        from scorer.protocols import get_judge_appendix

        appendix = get_judge_appendix()
        if appendix is not None:
            _write_judge_resource_appendix(run_dir, appendix)

    sys.stdout.write(render_curve(per_question, epsilon=args.epsilon))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
