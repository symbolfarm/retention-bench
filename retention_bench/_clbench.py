"""Single chokepoint for importing Continual Learning Bench (CL-Bench).

CL-Bench's distribution is published under the import path ``src`` (its
``pyproject`` literally packages a top-level ``src`` package). Importing
``from src.*`` throughout ``retention_bench`` would be fragile: any local
``src/`` directory on ``sys.path`` shadows it, and the intent (this is *the
benchmark*, not "some src dir") is opaque at every call site.

So every CL-Bench symbol ``retention_bench`` needs is re-exported here, once.
The rest of the package imports from ``retention_bench._clbench`` and never
touches ``src.*`` directly. If/when CL-Bench renames its distribution (a
candidate upstream contribution), this is the only file that changes.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

try:
    from src.interface import (  # noqa: F401
        ContinualLearningSystem,
        ContinualLearningTask,
        EvalMetrics,
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
    from src.registry import get_task_class as _clbench_get_task_class
    from src.registry import list_tasks as _clbench_list_tasks
    from src.runtime.runner import run_task  # noqa: F401
    from src.tasks.blind_spectrum_monitoring.corpus import (  # noqa: F401
        build_rollout_corpus,
        default_corpus_paths,
        write_scan_corpus,
    )
    from src.trace_metrics import build_benchmark_aggregate  # noqa: F401
    from src.usage import UsageEvent  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - exercised via env, not unit
    raise ModuleNotFoundError(
        "retention_bench requires Continual Learning Bench (the 'cl-benchmark' "
        "distribution, import path 'src'; Python >= 3.13). Install the pinned "
        "commit from this repo's pyproject.toml *editable* so its task data "
        "files (templates/variants/schedules) are present on disk — a plain "
        "wheel install silently drops them:\n"
        "    pip install -e 'git+https://github.com/pgasawa/"
        "continual-learning-bench.git@<pinned-sha>#egg=cl-benchmark'\n"
        "(see the cl-benchmark pin in pyproject.toml for the exact SHA), or "
        "run under an interpreter/venv that already has it."
    ) from exc


def _local_tasks() -> dict[str, type[ContinualLearningTask]]:
    from retention_bench.tasks import LOCAL_TASKS

    return LOCAL_TASKS


def get_task_class(name: str) -> type[ContinualLearningTask]:
    """Resolve a task from CL-Bench first, then Retention Bench-owned tasks."""
    try:
        return _clbench_get_task_class(name)
    except KeyError:
        local = _local_tasks()
        if name in local:
            return local[name]
        raise


def list_tasks() -> list[str]:
    """List upstream CL-Bench tasks plus Retention Bench-owned local tasks."""
    return sorted(set(_clbench_list_tasks()) | set(_local_tasks()))


def load_task_spec(spec: str) -> type[ContinualLearningTask]:
    """Resolve a *bring-your-own* task from a ``TARGET:ClassName`` spec.

    ``TARGET`` is either a dotted module path (``my_pkg.tasks``) importable by
    this (harness) interpreter, or a path to a ``.py`` file (``/abs/task.py`` or
    ``./rel/task.py``). This lets a SUT repo ship its own task without editing
    retention-bench.

    The task is imported and run **in the harness process**, not the SUT
    subprocess, so the file must be importable here: keep it dependency-light
    (pydantic/stdlib; no torch). Raises ``ValueError`` / ``FileNotFoundError`` /
    ``ImportError`` / ``AttributeError`` / ``TypeError`` with an actionable
    message; the CLI converts these to ``parser.error``.
    """
    if ":" not in spec:
        raise ValueError(
            f"task-spec must be 'module:Class' or '/path/to/file.py:Class', got {spec!r}"
        )
    target, _, cls_name = spec.rpartition(":")
    if not target or not cls_name:
        raise ValueError(
            f"task-spec must be 'module:Class' or '/path/to/file.py:Class', got {spec!r}"
        )

    looks_like_file = target.endswith(".py") or os.sep in target or target.startswith(".")
    if looks_like_file:
        path = Path(target).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"task-spec file not found: {path}")
        mod_name = f"_rb_byo_task_{path.stem}"
        module_spec = importlib.util.spec_from_file_location(mod_name, path)
        if module_spec is None or module_spec.loader is None:
            raise ImportError(f"could not load task module from {path}")
        module = importlib.util.module_from_spec(module_spec)
        # Register before exec so the module's own classes resolve their
        # __module__ (dataclasses, pickling, typing.get_type_hints all look the
        # module up in sys.modules during/after class definition).
        sys.modules[mod_name] = module
        module_spec.loader.exec_module(module)
    else:
        module = importlib.import_module(target)

    try:
        cls = getattr(module, cls_name)
    except AttributeError as exc:
        raise AttributeError(f"task class {cls_name!r} not found in {target!r}") from exc
    if not (isinstance(cls, type) and issubclass(cls, ContinualLearningTask)):
        raise TypeError(
            f"{cls_name!r} from {target!r} is not a ContinualLearningTask subclass"
        )
    return cls


__all__ = [
    "ContinualLearningSystem",
    "ContinualLearningTask",
    "EvalMetrics",
    "InstanceOutcome",
    "Observation",
    "Query",
    "Response",
    "TaskResult",
    "TaskStepResult",
    "UsageEvent",
    "build_benchmark_aggregate",
    "build_rollout_corpus",
    "default_corpus_paths",
    "get_task_class",
    "list_tasks",
    "load_task_spec",
    "observation_marks_instance_complete",
    "run_task",
    "serialize_instance_outcome",
    "standard_evaluate",
    "write_scan_corpus",
]
