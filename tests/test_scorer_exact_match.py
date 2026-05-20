"""Exact-match scorer edge cases: case, whitespace, punctuation."""

from __future__ import annotations

import pytest

from scorer.exact_match import exact_match_score, score_record


@pytest.mark.parametrize(
    "sut,gold",
    [
        ("travelling salesman", "travelling salesman"),
        ("Travelling Salesman", "travelling salesman"),  # case
        ("  travelling   salesman  ", "travelling salesman"),  # whitespace
        ("travelling\tsalesman", "travelling salesman"),  # tab
        ("travelling-salesman", "travelling salesman"),  # punctuation
        ("travelling salesman.", "travelling salesman"),  # trailing punct
        ('"travelling salesman"', "travelling salesman"),  # quotes
        ("travelling salesman", "Travelling Salesman!"),  # both messy
    ],
)
def test_exact_match_positive(sut: str, gold: str) -> None:
    assert exact_match_score(sut, gold) == 1.0


@pytest.mark.parametrize(
    "sut,gold",
    [
        ("salesman", "travelling salesman"),
        ("", "travelling salesman"),
        ("travelling salesmen", "travelling salesman"),  # off by one letter
        ("Unknown", "travelling salesman"),
    ],
)
def test_exact_match_negative(sut: str, gold: str) -> None:
    assert exact_match_score(sut, gold) == 0.0


def test_score_record_ok() -> None:
    rec = {
        "question_id": "q1",
        "probe_type": "ceiling",
        "sut_answer": "Travelling Salesman.",
        "gold_answer": "travelling salesman",
        "parsing_status": "ok",
    }
    out = score_record(rec)
    assert out["score"] == 1.0
    # Original fields preserved.
    assert out["question_id"] == "q1"


def test_score_record_not_found_scores_zero() -> None:
    rec = {
        "question_id": "q1",
        "probe_type": "ceiling",
        "sut_answer": "",
        "gold_answer": "travelling salesman",
        "parsing_status": "not_found",
    }
    out = score_record(rec)
    assert out["score"] == 0.0
    # parsing_status preserved for diagnostics.
    assert out["parsing_status"] == "not_found"


def test_score_record_ambiguous_scores_zero() -> None:
    # Even if the (first-occurrence) answer matches gold, ambiguous → 0.
    rec = {
        "question_id": "q1",
        "probe_type": "ceiling",
        "sut_answer": "travelling salesman",
        "gold_answer": "travelling salesman",
        "parsing_status": "ambiguous",
    }
    assert score_record(rec)["score"] == 0.0
