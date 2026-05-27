"""Scorer protocol and dispatcher.

Defines the ``Scorer`` protocol (``score(record) -> (score, scorer_kind,
rationale|None)``) and the dispatch table mapping ``question_type`` to a
``Scorer`` implementation.

Dispatch rules (locked per B3 design decisions):

- ``surface_factual``  → ``ExactMatchScorer``
- ``entity_tracking``  → ``JudgeScorer``
- ``multi_hop``        → ``JudgeScorer``
- unknown / unmapped   → hard error (``ValueError``)

``ExactMatchScorer`` wraps the existing :func:`scorer.exact_match.exact_match_score`
logic and never calls an API.

The ``JudgeScorer`` lives in :mod:`scorer.judge` and calls the Anthropic API.
A future ``DeepEvalScorer`` (B9 / B7 follow-up) would add another implementation
without touching this file's dispatch table shape or the callers in
``scorer.aggregate``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Tuple

from scorer.exact_match import exact_match_score


# ---------------------------------------------------------------------------
# Scorer protocol
# ---------------------------------------------------------------------------


class Scorer(Protocol):
    """A pure-function interface for per-record scoring.

    Implementations must be importable without network access (the judge
    implementation instantiates the API client lazily).
    """

    def score(self, record: Dict[str, Any]) -> Tuple[float, str, Optional[str]]:
        """Score a single ``questions.jsonl`` record.

        Returns
        -------
        score : float
            0.0–1.0 (binary for exact-match, potentially fractional for
            judge if we ever adopt soft scoring — currently always 0 or 1).
        scorer_kind : str
            Opaque label written to the scored record (e.g.
            ``"exact_match"`` or ``"judge"``).
        rationale : str | None
            Human-readable rationale (None for exact-match; populated by
            the judge).
        """
        ...


# ---------------------------------------------------------------------------
# ExactMatchScorer
# ---------------------------------------------------------------------------


class ExactMatchScorer:
    """Scorer that uses case-insensitive, whitespace-normalised exact match."""

    def score(self, record: Dict[str, Any]) -> Tuple[float, str, Optional[str]]:
        parsing_status = record.get("parsing_status", "ok")
        if parsing_status != "ok":
            return 0.0, "exact_match", None
        s = exact_match_score(
            record.get("sut_answer", "") or "",
            record.get("gold_answer", "") or "",
        )
        return s, "exact_match", None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

# Question types that use exact-match.
_EXACT_MATCH_TYPES: frozenset[str] = frozenset({"surface_factual"})

# Question types that use the judge. All types NOT in _EXACT_MATCH_TYPES that
# we know about must be listed here. Unknown types → hard error.
_JUDGE_TYPES: frozenset[str] = frozenset({"entity_tracking", "multi_hop"})

_ALL_KNOWN_TYPES: frozenset[str] = _EXACT_MATCH_TYPES | _JUDGE_TYPES

# Singletons — exact-match scorer is stateless; judge scorer is instantiated
# lazily by get_scorer() on first judge-mode call.
_EXACT_MATCH_SCORER = ExactMatchScorer()
_judge_scorer_instance: "Any | None" = None  # populated on first judge request


def get_scorer(question_type: str, scorer_mode: str = "auto") -> Scorer:
    """Return the appropriate :class:`Scorer` for *question_type*.

    Parameters
    ----------
    question_type:
        Value from the ``question_type`` field of a ``questions.jsonl`` record.
    scorer_mode:
        ``"auto"``        — dispatch per the locked table above.
        ``"exact-match"`` — always return :class:`ExactMatchScorer` (default
                            CLI mode; reproduces M6 behavior exactly).
        ``"judge"``       — always use judge for judge-eligible types; still
                            uses exact-match for ``surface_factual`` per the
                            locked dispatch (surface_factual bypasses judge by
                            design regardless of CLI flag).

    Raises
    ------
    ValueError
        If *question_type* is not in ``_ALL_KNOWN_TYPES`` (hard error — fail
        loud, do not silently fall back).
    """
    if question_type not in _ALL_KNOWN_TYPES:
        raise ValueError(
            f"Unknown question_type {question_type!r}. "
            f"Known types: {sorted(_ALL_KNOWN_TYPES)}. "
            "Add to _EXACT_MATCH_TYPES or _JUDGE_TYPES in scorer/protocols.py."
        )

    # surface_factual always goes to exact-match regardless of scorer_mode.
    if question_type in _EXACT_MATCH_TYPES:
        return _EXACT_MATCH_SCORER

    # Judge-eligible type: respect scorer_mode.
    if scorer_mode == "exact-match":
        return _EXACT_MATCH_SCORER

    # scorer_mode is "auto" or "judge" — use judge for judge-eligible types.
    global _judge_scorer_instance
    if _judge_scorer_instance is None:
        from scorer.judge import JudgeScorer  # deferred to avoid import-time API key check
        _judge_scorer_instance = JudgeScorer()
    return _judge_scorer_instance


def reset_judge_singleton() -> None:
    """Reset the cached judge singleton — used in tests to inject a fresh scorer."""
    global _judge_scorer_instance
    _judge_scorer_instance = None


def get_judge_appendix() -> "Optional[Dict[str, Any]]":
    """Return the judge's accumulated ``resource_appendix`` for the run, or
    ``None`` if the judge was never engaged (e.g. exact-match mode, or a judge
    run that only contained ``surface_factual`` records).

    The CLI calls this after :func:`scorer.aggregate.aggregate_records` to
    write the ``judge_resource_appendix.jsonl`` sibling (B11).
    """
    if _judge_scorer_instance is None:
        return None
    return _judge_scorer_instance.resource_appendix()
