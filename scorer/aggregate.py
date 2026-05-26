"""Aggregate per-question records into ``(P, C, R(k))`` tables and the
normalised retention curve.

Follows ``docs/metrics.md``:

- ``P(q)`` from the ``prior`` probe, ``C(q)`` from ``ceiling``, ``R(k, q)``
  from ``retention`` probes at each ``k``.
- ``normalised_retention(k, q) = (R(k, q) − P(q)) / max(C(q) − P(q), ε)``.
- Questions where ``C(q) − P(q) < ε`` are reported but excluded from the
  aggregate, per the metrics.md exclusion rule.

Scorer dispatch
---------------
By default (``scorer_mode="exact-match"``) all records are scored with
:class:`scorer.protocols.ExactMatchScorer`, reproducing M6 behavior exactly.

When ``scorer_mode="judge"`` is passed, judge-eligible question types
(``entity_tracking``, ``multi_hop``) are routed to :class:`scorer.judge.JudgeScorer`
while ``surface_factual`` still uses exact-match.  Per-record results gain
``scorer_kind`` (always) and — for judge-scored records — ``judge_rationale``.

Judge rationales are NOT written to ``questions.jsonl`` here; the CLI
(__main__.py) writes them to a sibling ``scoring.jsonl``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from scorer.protocols import get_scorer

# Default epsilon for the "no learnable signal" exclusion. The metrics doc
# suggests "typical ε = 0.05 of the score range"; exact-match scores live
# in {0, 1}, so 0.05 reads as "at least 5% of the score range".
EPSILON: float = 0.05


@dataclass
class QuestionAggregate:
    """Per-question rollup of ``P``, ``C``, and ``R(k)`` instances."""

    question_id: str
    prior: Optional[float] = None
    ceiling: Optional[float] = None
    # k -> score. If a (question, k) appears more than once (multiple seeds /
    # retention probes at the same k), the mean is taken at consume time.
    retention: Dict[int, List[float]] = field(default_factory=dict)

    @property
    def gap(self) -> Optional[float]:
        if self.prior is None or self.ceiling is None:
            return None
        return self.ceiling - self.prior

    def is_excluded(self, epsilon: float = EPSILON) -> bool:
        """``True`` if the question has no learnable signal (``C − P < ε``)."""
        gap = self.gap
        if gap is None:
            # Missing P or C — can't normalise. Treat as excluded.
            return True
        return gap < epsilon

    def retention_at(self, k: int) -> Optional[float]:
        """Mean retention score at ``k`` (None if no probe at this ``k``)."""
        scores = self.retention.get(k)
        if not scores:
            return None
        return sum(scores) / len(scores)

    def k_values(self) -> List[int]:
        return sorted(self.retention.keys())


def normalised_retention(
    r: float, p: float, c: float, epsilon: float = EPSILON
) -> float:
    """``(R − P) / max(C − P, ε)``. Caller is responsible for ε-exclusion."""
    return (r - p) / max(c - p, epsilon)


def aggregate_records(
    records: Iterable[Dict[str, Any]],
    scorer_mode: str = "exact-match",
) -> Tuple[List[Dict[str, Any]], Dict[str, QuestionAggregate]]:
    """Score and aggregate a stream of ``questions.jsonl`` records.

    Parameters
    ----------
    records:
        Iterable of ``questions.jsonl`` records.
    scorer_mode:
        ``"exact-match"`` (default) — exact-match for all types,
        reproducing M6 behavior exactly.
        ``"judge"`` — routes judge-eligible types to the LLM judge.

    Returns ``(scored_records, per_question)`` where:

    - ``scored_records`` is the input list with ``score`` and ``scorer_kind``
      fields added (and ``judge_rationale`` for judge-scored records).
    - ``per_question`` maps ``question_id`` to its ``QuestionAggregate``.
    """
    scored: List[Dict[str, Any]] = []
    per_question: Dict[str, QuestionAggregate] = {}

    for record in records:
        question_type = record.get("question_type", "surface_factual")
        scorer = get_scorer(question_type, scorer_mode=scorer_mode)
        score_val_f, scorer_kind, rationale = scorer.score(record)

        s = dict(record)
        s["score"] = score_val_f
        s["scorer_kind"] = scorer_kind
        if rationale is not None:
            s["judge_rationale"] = rationale
        scored.append(s)

        qid = s.get("question_id")
        if qid is None:
            continue
        agg = per_question.setdefault(qid, QuestionAggregate(question_id=qid))
        probe = s.get("probe_type")

        if probe == "prior":
            # If multiple priors land for the same question (shouldn't happen
            # in a well-formed run, but be defensive), keep the first.
            if agg.prior is None:
                agg.prior = score_val_f
        elif probe == "ceiling":
            if agg.ceiling is None:
                agg.ceiling = score_val_f
        elif probe == "retention":
            k = s.get("k")
            if k is None:
                # Malformed: retention probe without k. Skip — metrics.md
                # treats k as load-bearing for the curve axis.
                continue
            agg.retention.setdefault(int(k), []).append(score_val_f)
        # Unknown probe types are ignored (forward-compat).

    return scored, per_question


def aggregate_curve(
    per_question: Dict[str, QuestionAggregate],
    epsilon: float = EPSILON,
) -> Dict[int, Tuple[float, int]]:
    """Aggregate normalised retention across questions, per ``k``.

    Returns ``{k: (mean_normalised_retention, n_usable)}``. Excluded
    questions (``C ≈ P``) are dropped from the per-k aggregate.
    """
    out: Dict[int, Tuple[float, int]] = {}
    # Discover all k values that appear in any question.
    all_ks: set[int] = set()
    for agg in per_question.values():
        all_ks.update(agg.retention.keys())

    for k in sorted(all_ks):
        values: List[float] = []
        for agg in per_question.values():
            if agg.is_excluded(epsilon):
                continue
            r = agg.retention_at(k)
            if r is None:
                continue
            assert agg.prior is not None and agg.ceiling is not None
            values.append(normalised_retention(r, agg.prior, agg.ceiling, epsilon))
        if values:
            out[k] = (sum(values) / len(values), len(values))
    return out
