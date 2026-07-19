"""Retention-curve band primitives: the normalised-retention formula + ε.

The book-track per-question aggregation (``aggregate_records`` /
``aggregate_curve`` / ``aggregate_curve_by_type`` and the ``QuestionAggregate``
rollup) was retired with the book-track scorer. Only the band math
survives, because it is all the CL-Bench-native ``gain_curve`` path needs;
``test_gain_curve`` exercises it in the reset-axis context.
"""

from __future__ import annotations

from scorer.aggregate import EPSILON, normalised_retention


def test_normalised_retention_formula() -> None:
    # (R − P) / max(C − P, ε)
    assert normalised_retention(1.0, 0.0, 1.0) == 1.0
    assert normalised_retention(0.0, 0.0, 1.0) == 0.0
    assert normalised_retention(0.5, 0.0, 1.0) == 0.5
    # Negative: post-reset below prior.
    assert normalised_retention(0.0, 1.0, 1.0, epsilon=0.05) == (0.0 - 1.0) / 0.05


def test_normalised_retention_floors_band_at_epsilon() -> None:
    # When the raw band C − P is below ε, the denominator is clamped to ε so the
    # formula never divides by a vanishing (or negative) band.
    assert normalised_retention(0.5, 0.0, 0.0, epsilon=0.05) == 0.5 / 0.05


def test_epsilon_constant() -> None:
    # Lock the default so a silent change in the module triggers a test
    # failure rather than a quiet metrics drift.
    assert EPSILON == 0.05
