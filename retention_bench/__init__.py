"""retention_bench — Continual Learning Bench extension: hard reset + compute.

retention_bench is the productionised form of the C0 spike: it makes our
process-contract SUTs runnable through Continual Learning Bench's runner, adds a
hard RESET discontinuity (process kill where only the on-disk survive-dir
persists), a system-side reset *schedule* (arbitrary reset density ``k``), and
``compute`` usage accounting (FLOPs + survive-dir storage).

Requires Python >=3.13 and the ``cl-benchmark`` distribution (import path
``src``); see ``retention_bench._clbench``.
"""

from __future__ import annotations

from .reset_schedule import (
    EveryNInstances,
    ExplicitBoundaries,
    NoReset,
    ResetSchedule,
)
from .system import SubprocessSystem

__all__ = [
    "SubprocessSystem",
    "ResetSchedule",
    "NoReset",
    "EveryNInstances",
    "ExplicitBoundaries",
]
