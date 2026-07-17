"""Backward-compatible shim over :mod:`retention_bench.scoring`.

RB-11 folded the band formula (``EPSILON`` + ``normalised_retention``) into
the ``retention_bench`` package proper — ``scorer`` was never included in the
packaged distribution (``pyproject.toml``'s ``packages.find`` only lists
``harness*``/``retention_bench*``), so shipped code importing from ``scorer``
broke non-editable installs (2026-07-07 v0.1 review, finding 4). This module
now just re-exports the real implementation so dev-tree imports of
``scorer.aggregate`` (``scorer/__init__.py``, ``tests/test_scorer_aggregate.py``)
keep working unchanged.
"""

from __future__ import annotations

from retention_bench.scoring import EPSILON, normalised_retention

__all__ = [
    "EPSILON",
    "normalised_retention",
]
