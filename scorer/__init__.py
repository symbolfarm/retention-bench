"""Retention-bench scorer package.

Reduced by C20 to the retention-curve band primitives
(:data:`~scorer.aggregate.EPSILON`, :func:`~scorer.aggregate.normalised_retention`)
that :mod:`retention_bench.gain_curve` normalises against. The book-track
per-question scorer (exact-match / judge dispatch, ``(P, C, R(k))`` aggregation,
and the ``python -m scorer`` CLI) was retired with the book-track harness; see
``docs/metrics.md`` for the metric and ``.tasks/debriefs/C20-*`` for the cutover.
"""

from scorer.aggregate import EPSILON, normalised_retention

__all__ = [
    "EPSILON",
    "normalised_retention",
]
