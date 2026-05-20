"""Retention-bench scorer package.

Pure consumer of the trace data contract: reads ``<run-dir>/questions.jsonl``
and emits per-question score records, a ``(P, C, R(k))`` table per question,
and an aggregate normalised retention curve.

The scorer never imports from ``harness/`` and never touches ``trace.jsonl``
or stage payloads — see ``docs/trace-schema.md`` and ``.tasks/debriefs/M6.md``.
"""

from scorer.exact_match import exact_match_score, score_record
from scorer.aggregate import (
    EPSILON,
    QuestionAggregate,
    aggregate_records,
    normalised_retention,
)
from scorer.curve import render_curve

__all__ = [
    "EPSILON",
    "QuestionAggregate",
    "aggregate_records",
    "exact_match_score",
    "normalised_retention",
    "render_curve",
    "score_record",
]
