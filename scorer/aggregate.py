"""Retention-curve band normalisation primitives.

The single shared home for the ``(R − P) / max(C − P, ε)`` band formula and its
exclusion threshold ``ε``. :mod:`retention_bench.gain_curve` imports both from
here so the reset-axis curve and any future consumer normalise against one
definition rather than re-deriving a competing one.

Follows ``docs/metrics.md``:

- ``normalised_retention(R, P, C) = (R − P) / max(C − P, ε)``.
- A band where ``C − P < ε`` has no learnable signal; the caller is responsible
  for excluding it (``gain_curve`` reports ``None`` for such points).

History: the book-track scorer (retired by C20) layered per-``question_type``
``(P, C, R(k))`` aggregation on top of these primitives. That aggregation, the
exact-match/judge scorer dispatch, and the ``python -m scorer`` CLI are gone;
only the band math survives, because it is all the CL-Bench-native path needs.
"""

from __future__ import annotations

# Default epsilon for the "no learnable signal" exclusion. The metrics doc
# suggests "typical ε = 0.05 of the score range"; binary rewards live in
# {0, 1}, so 0.05 reads as "at least 5% of the score range".
EPSILON: float = 0.05


def normalised_retention(
    r: float, p: float, c: float, epsilon: float = EPSILON
) -> float:
    """``(R − P) / max(C − P, ε)``. Caller is responsible for ε-exclusion."""
    return (r - p) / max(c - p, epsilon)
