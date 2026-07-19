"""Retention-bench scorer package.

Reduced to the retention-curve band primitives
(:data:`~scorer.aggregate.EPSILON`, :func:`~scorer.aggregate.normalised_retention`)
that :mod:`retention_bench.gain_curve` normalises against. The earlier
per-question scorer (exact-match / judge dispatch, ``(P, C, R(k))`` aggregation,
and the ``python -m scorer`` CLI) was retired with the pre-pivot book-track
harness; see ``docs/metrics.md`` for the metric.
"""

from scorer.aggregate import EPSILON, normalised_retention

__all__ = [
    "EPSILON",
    "normalised_retention",
]
