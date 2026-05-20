"""Scorer entry point: ``python -m scorer <run-dir>``.

Reads ``<run-dir>/questions.jsonl`` (the per-question records file from the
M2/M4 harness — see ``docs/trace-schema.md``), scores each record with the
exact-match scorer, aggregates per-question, and prints the retention table
to stdout.

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
    _, per_question = aggregate_records(records)
    sys.stdout.write(render_curve(per_question, epsilon=args.epsilon))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
