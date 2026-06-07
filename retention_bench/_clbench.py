"""Single chokepoint for importing Continual Learning Bench (CL-Bench).

CL-Bench's distribution is published under the import path ``src`` (its
``pyproject`` literally packages a top-level ``src`` package — a packaging
smell flagged in the C0 spike and the C2 brief). Importing ``from src.*``
throughout ``retention_bench`` would be fragile: any local ``src/`` directory
on ``sys.path`` shadows it, and the intent (this is *the benchmark*, not "some
src dir") is opaque at every call site.

So every CL-Bench symbol ``retention_bench`` needs is re-exported here, once.
The rest of the package imports from ``retention_bench._clbench`` and never
touches ``src.*`` directly. If/when CL-Bench renames its distribution (a
candidate C7 upstream PR), this is the only file that changes.
"""

from __future__ import annotations

try:
    from src.interface import (  # noqa: F401
        ContinualLearningSystem,
        ContinualLearningTask,
        InstanceOutcome,
        Observation,
        Query,
        Response,
        TaskResult,
        TaskStepResult,
        observation_marks_instance_complete,
        serialize_instance_outcome,
        standard_evaluate,
    )
    from src.registry import get_task_class, list_tasks  # noqa: F401
    from src.runtime.runner import run_task  # noqa: F401
    from src.trace_metrics import build_benchmark_aggregate  # noqa: F401
    from src.usage import UsageEvent  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - exercised via env, not unit
    raise ModuleNotFoundError(
        "retention_bench requires Continual Learning Bench (the 'cl-benchmark' "
        "distribution, import path 'src'). It is a Python>=3.13 dependency and is "
        "not installed in this interpreter. Install it (pinned) with:\n"
        "    pip install -e '.[/* see pyproject: cl-benchmark @ git+... */]'\n"
        "or run against the 3.13 venv that already has it, e.g.\n"
        "    PYTHONPATH=/workspace /home/agent/src/cl-bench/.venv/bin/python ..."
    ) from exc


__all__ = [
    "ContinualLearningSystem",
    "ContinualLearningTask",
    "InstanceOutcome",
    "Observation",
    "Query",
    "Response",
    "TaskResult",
    "TaskStepResult",
    "UsageEvent",
    "build_benchmark_aggregate",
    "get_task_class",
    "list_tasks",
    "observation_marks_instance_complete",
    "run_task",
    "serialize_instance_outcome",
    "standard_evaluate",
]
