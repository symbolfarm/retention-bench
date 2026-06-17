"""Retention Bench-owned CL-Bench tasks."""

from __future__ import annotations

from .symbolic_associative_retention import SymbolicAssociativeRetentionTask

LOCAL_TASKS = {
    "symbolic_associative_retention": SymbolicAssociativeRetentionTask,
}

__all__ = ["LOCAL_TASKS", "SymbolicAssociativeRetentionTask"]
