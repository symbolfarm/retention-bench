"""Aggregate logic: normalised retention math + C≈P exclusion."""

from __future__ import annotations

from scorer.aggregate import (
    EPSILON,
    aggregate_curve,
    aggregate_records,
    normalised_retention,
)


def _rec(qid: str, probe: str, sut: str, gold: str, k: int | None = None) -> dict:
    return {
        "record_id": f"evt-{qid}-{probe}",
        "event_id": f"evt-{probe}",
        "question_id": qid,
        "probe_type": probe,
        "k": k,
        "question_text": "?",
        "gold_answer": gold,
        "sut_answer": sut,
        "question_type": "surface_factual",
        "material_ref": "m1",
        "question_seen_before": 0,
        "parsing_status": "ok",
    }


def test_normalised_retention_formula() -> None:
    # (R − P) / max(C − P, ε)
    assert normalised_retention(1.0, 0.0, 1.0) == 1.0
    assert normalised_retention(0.0, 0.0, 1.0) == 0.0
    assert normalised_retention(0.5, 0.0, 1.0) == 0.5
    # Negative: post-reset below prior.
    assert normalised_retention(0.0, 1.0, 1.0, epsilon=0.05) == (0.0 - 1.0) / 0.05


def test_aggregate_records_collects_pcr() -> None:
    # q1: learnable; P=0, C=1, R(1)=1 → norm 1.0
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        _rec("q1", "retention", "right", "right", k=1),
    ]
    _, per_q = aggregate_records(records)
    agg = per_q["q1"]
    assert agg.prior == 0.0
    assert agg.ceiling == 1.0
    assert agg.retention_at(1) == 1.0
    assert not agg.is_excluded()


def test_aggregate_excludes_c_approx_p() -> None:
    # q1: learnable (P=0, C=1)
    # q2: not learnable (P=1, C=1) → excluded from aggregate
    # q3: not learnable (P=0, C=0) → excluded from aggregate
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        _rec("q1", "retention", "right", "right", k=1),
        _rec("q2", "prior", "right", "right"),
        _rec("q2", "ceiling", "right", "right"),
        _rec("q2", "retention", "right", "right", k=1),
        _rec("q3", "prior", "wrong", "right"),
        _rec("q3", "ceiling", "wrong", "right"),
        _rec("q3", "retention", "wrong", "right", k=1),
    ]
    _, per_q = aggregate_records(records)
    assert per_q["q1"].is_excluded() is False
    assert per_q["q2"].is_excluded() is True
    assert per_q["q3"].is_excluded() is True

    curve = aggregate_curve(per_q)
    # Only q1 contributes.
    assert curve == {1: (1.0, 1)}


def test_aggregate_curve_mean_across_questions() -> None:
    # q1: P=0, C=1, R(1)=1 → norm 1.0
    # q2: P=0, C=1, R(1)=0 → norm 0.0
    # mean at k=1 = 0.5 over 2 usable questions.
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        _rec("q1", "retention", "right", "right", k=1),
        _rec("q2", "prior", "wrong", "right"),
        _rec("q2", "ceiling", "right", "right"),
        _rec("q2", "retention", "wrong", "right", k=1),
    ]
    _, per_q = aggregate_records(records)
    curve = aggregate_curve(per_q)
    assert curve[1] == (0.5, 2)


def test_aggregate_handles_multiple_k() -> None:
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        _rec("q1", "retention", "right", "right", k=1),
        _rec("q1", "retention", "wrong", "right", k=2),
    ]
    _, per_q = aggregate_records(records)
    assert per_q["q1"].retention_at(1) == 1.0
    assert per_q["q1"].retention_at(2) == 0.0
    curve = aggregate_curve(per_q)
    assert curve[1] == (1.0, 1)
    assert curve[2] == (0.0, 1)


def test_parsing_status_failures_score_zero() -> None:
    # not_found / ambiguous should score 0 even if the sut_answer happens
    # to match the gold.
    records = [
        _rec("q1", "prior", "wrong", "right"),
        _rec("q1", "ceiling", "right", "right"),
        {
            **_rec("q1", "retention", "right", "right", k=1),
            "parsing_status": "not_found",
        },
    ]
    _, per_q = aggregate_records(records)
    assert per_q["q1"].retention_at(1) == 0.0


def test_missing_p_or_c_is_excluded() -> None:
    records = [
        _rec("q1", "prior", "wrong", "right"),
        # No ceiling.
        _rec("q1", "retention", "right", "right", k=1),
    ]
    _, per_q = aggregate_records(records)
    assert per_q["q1"].is_excluded() is True
    assert aggregate_curve(per_q) == {}


def test_epsilon_constant() -> None:
    # Lock the default so a silent change in the module triggers a test
    # failure rather than a quiet metrics drift.
    assert EPSILON == 0.05
