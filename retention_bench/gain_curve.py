"""Reset-axis reporting: retention/gain as a function of hard-reset count ``k``.

This is the net-new measurement axis the pivot promised (see
``docs/clbench-pivot-plan.md``). CL-Bench reports a single ``mean_gain``
(stateful reward minus a stateless baseline) at one implicit reset density; it
has no ``k``-axis. We add one: run the same system at a *sweep* of hard-reset
densities and plot how retention holds up as resets accumulate.

### The curve

For one task + system we run three kinds of arm, each from a *fresh* survive-dir:

* **ceiling ``C``** — :class:`~retention_bench.NoReset`, ``wipe_on_reset=False``.
  State accumulates unbroken; this is the best the system can do (``R(0)``).
* **prior ``P``** — :class:`~retention_bench.EveryNInstances` ``(1)`` with
  ``wipe_on_reset=True``. The survive-dir is wiped on every boundary, so each
  instance is seen by a fresh, stateless process. This is CL-Bench's stateless
  baseline expressed in our hard-reset vocabulary.
* **points ``R(k)``** — one stateful (non-wiping) arm per requested schedule.
  ``k`` is the *measured* number of hard resets the run actually executed
  (``system.scheduled_resets``), not the schedule's nominal density.

Normalised retention at each point is

    norm_gain(k) = (R(k) − P) / max(C − P, ε)

— exactly :func:`retention_bench.scoring.normalised_retention`, the same band
normalisation the book-track scorer used before RB-11 folded it into this
package. We reuse it verbatim rather than defining a competing formula.

### Reconciliation with CL-Bench

The brief asks us to confirm the axis *reduces* to CL-Bench's gain at the
matching ``k``. Their normalised gain is ``(r_sf − r_sl) / (r_max − r_sl)``;
under the substitution ``r_sf → R(k)``, ``r_sl → P``, ``r_max → C`` that is our
formula. The non-tautological check is on the *numerator*: our ``R(k) − P``
(a difference of run-mean rewards) must equal CL-Bench's ``mean_gain``, which
its own :func:`build_benchmark_aggregate` computes as the mean of *per-instance*
``rollout_reward − baseline_reward`` matched by ``instance_id``. The two agree
exactly because both arms play the identical instance set, so the mean of the
per-instance differences equals the difference of the means. Each
:class:`GainCurvePoint` carries ``clbench_mean_gain`` straight from their
function so the equality is checkable on every run (see ``tests``).
"""

from __future__ import annotations

import argparse
import shlex
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from .scoring import EPSILON, normalised_retention

from ._clbench import (
    ContinualLearningTask,
    build_benchmark_aggregate,
    get_task_class,
    list_tasks,
    load_task_spec,
    run_task,
    serialize_instance_outcome,
)
from .reset_schedule import (
    EveryNInstances,
    ExplicitBoundaries,
    NoReset,
    ResetSchedule,
)
from .system import SubprocessSystem

# A factory that builds a fresh system bound to ``state_dir`` for one arm. The
# driver owns survive-dir isolation (one empty dir per arm), so the factory only
# varies the schedule + wipe behaviour; everything else (command, name, timeout,
# PYTHONPATH) is closed over by the caller.
MakeSystem = Callable[[Path, ResetSchedule, bool], SubprocessSystem]
MakeTask = Callable[[], ContinualLearningTask]


@dataclass
class GainCurvePoint:
    """One stateful arm of the sweep."""

    k: int
    """Measured number of hard resets the run executed (``scheduled_resets``)."""
    schedule_label: str
    mean_reward: float
    """``R(k)``: mean per-instance reward over the run."""
    n_instances: int
    normalised_gain: Optional[float]
    """``(R(k) − P) / max(C − P, ε)``; ``None`` when the band is excluded."""
    clbench_mean_gain: float
    """CL-Bench's ``mean_gain`` vs the prior baseline — the reconciliation value."""
    outcomes: list[dict[str, Any]] = field(default_factory=list, repr=False)
    """Serialised per-instance outcomes, kept for post-hoc reanalysis."""


@dataclass
class GainCurve:
    """A reset-axis retention curve plus the band it normalises against."""

    system_name: str
    prior: float
    """``P`` — stateless-baseline mean reward."""
    ceiling: float
    """``C`` — no-reset (k=0) mean reward."""
    epsilon: float
    points: list[GainCurvePoint]
    prior_outcomes: list[dict[str, Any]] = field(default_factory=list, repr=False)
    ceiling_outcomes: list[dict[str, Any]] = field(default_factory=list, repr=False)

    @property
    def band(self) -> float:
        """``C − P`` — the learnable band the curve normalises against."""
        return self.ceiling - self.prior

    @property
    def excluded(self) -> bool:
        """``True`` if there is no learnable band (``C − P < ε``).

        Mirrors the ``retention_bench.scoring`` exclusion rule: with no band, the
        normalised curve is undefined and every point reports ``None``.
        """
        return self.band < self.epsilon


def clbench_mean_gain(
    baseline_outcomes: list[dict[str, Any]],
    rollout_outcomes: list[dict[str, Any]],
) -> float:
    """CL-Bench's own ``mean_gain`` for one rollout against a baseline.

    Thin wrapper over their :func:`build_benchmark_aggregate` so the
    reconciliation compares against the upstream implementation rather than a
    re-derivation. ``final_cumulative_mean_gain`` is the running mean of the
    per-instance gains at the last index = the mean per-instance gain.
    """
    aggregate = build_benchmark_aggregate(baseline_outcomes, [rollout_outcomes])
    return float(aggregate["final_cumulative_mean_gain"])


def run_reset_sweep(
    make_system: MakeSystem,
    make_task: MakeTask,
    reset_schedules: Sequence[ResetSchedule],
    *,
    system_name: str = "subprocess",
    state_root: Optional[Path] = None,
    epsilon: float = EPSILON,
) -> GainCurve:
    """Drive ``make_system``'s SUT through a sweep of reset schedules.

    Always runs a ceiling (``NoReset``, no wipe) and a prior (``EveryNInstances(1)``
    with wipe) arm to fix the band, then one stateful arm per entry in
    ``reset_schedules``. Each arm gets a fresh, empty survive-dir so state cannot
    leak between arms.

    Args:
        make_system: ``(state_dir, schedule, wipe_on_reset) -> SubprocessSystem``.
        make_task: ``() -> ContinualLearningTask``; called once per arm (the task
            holds per-run state, so each arm needs its own instance).
        reset_schedules: the stateful (non-wiping) arms to plot. Measured ``k``
            comes from each run; passing :class:`NoReset` yields a ``k=0`` point.
        system_name: label for the rendered curve.
        state_root: parent dir for the per-arm survive-dirs (a temp dir by default).
        epsilon: band-exclusion threshold (defaults to the scorer's ``EPSILON``).

    Returns:
        A :class:`GainCurve` with points sorted by measured ``k``.
    """
    root = Path(state_root) if state_root is not None else Path(tempfile.mkdtemp(prefix="gain-curve-"))
    root.mkdir(parents=True, exist_ok=True)

    def _run(label: str, schedule: ResetSchedule, wipe: bool) -> tuple[int, float, list[dict[str, Any]]]:
        state_dir = root / label
        state_dir.mkdir(parents=True, exist_ok=True)
        # Context manager so the final spawned process/container of each arm
        # is always reaped, not left to CPython refcounting + the weakref
        # finalizer (which can be delayed by GC or skipped under exceptions).
        with make_system(state_dir, schedule, wipe) as system:
            result = run_task(make_task(), system, show_progress=False, reset_between_instances=False)
            scheduled_resets = system.scheduled_resets
        outcomes = [serialize_instance_outcome(o) for o in result.instance_outcomes]
        return scheduled_resets, result.score, outcomes

    _, ceiling, ceiling_outcomes = _run("ceiling", NoReset(), False)
    _, prior, prior_outcomes = _run("prior", EveryNInstances(1), True)
    band = ceiling - prior

    points: list[GainCurvePoint] = []
    for i, schedule in enumerate(reset_schedules):
        k, mean_reward, outcomes = _run(f"arm_{i}_{schedule.label}", schedule, False)
        norm = normalised_retention(mean_reward, prior, ceiling, epsilon) if band >= epsilon else None
        points.append(
            GainCurvePoint(
                k=k,
                schedule_label=schedule.label,
                mean_reward=mean_reward,
                n_instances=len(outcomes),
                normalised_gain=norm,
                clbench_mean_gain=clbench_mean_gain(prior_outcomes, outcomes),
                outcomes=outcomes,
            )
        )

    points.sort(key=lambda p: p.k)
    return GainCurve(
        system_name=system_name,
        prior=prior,
        ceiling=ceiling,
        epsilon=epsilon,
        points=points,
        prior_outcomes=prior_outcomes,
        ceiling_outcomes=ceiling_outcomes,
    )


def render_curve(curve: GainCurve) -> str:
    """Render a :class:`GainCurve` as a plain-text table + band header."""
    lines = [
        f"Reset-axis retention curve  (system: {curve.system_name})",
        f"  prior   P  (stateless baseline) = {curve.prior:.4f}",
        f"  ceiling C  (no-reset, k=0)      = {curve.ceiling:.4f}",
        f"  band    C - P                   = {curve.band:.4f}"
        + ("   [EXCLUDED: < epsilon, curve undefined]" if curve.excluded else ""),
        "",
        f"  {'k':>3}  {'schedule':<16}  {'R(k)':>7}  {'norm_gain':>9}  {'clbench_gain':>12}  {'n':>3}",
        f"  {'-' * 3}  {'-' * 16}  {'-' * 7}  {'-' * 9}  {'-' * 12}  {'-' * 3}",
    ]
    for p in curve.points:
        norm = "    —    " if p.normalised_gain is None else f"{p.normalised_gain:>9.3f}"
        lines.append(
            f"  {p.k:>3}  {p.schedule_label:<16}  {p.mean_reward:>7.4f}  {norm}  "
            f"{p.clbench_mean_gain:>12.4f}  {p.n_instances:>3}"
        )
    lines.append("")
    lines.append(
        "  norm_gain = (R(k) - P) / max(C - P, eps);  "
        "clbench_gain = CL-Bench mean_gain vs prior (== R(k) - P)."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI: sweep any SUT command + CL-Bench task. SUT-agnostic — the SUT is an
# argument, so this drives the constructive SUT, the counter fixture, or any
# future SUT speaking the SubprocessSystem contract.
# --------------------------------------------------------------------------- #
def _parse_kwargs(pairs: list[str]) -> dict[str, Any]:
    """Parse ``key=value`` task kwargs, coercing int/float/bool where obvious."""
    out: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--task-kwarg must be key=value, got {pair!r}")
        key, raw = pair.split("=", 1)
        out[key] = _coerce(raw)
    return out


def _coerce(raw: str) -> Any:
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    return raw


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m retention_bench.gain_curve",
        description="Sweep a SUT over hard-reset densities and render the gain-vs-k curve.",
    )
    task_src = parser.add_mutually_exclusive_group()
    task_src.add_argument(
        "--task", help="CL-Bench or Retention Bench task name (see --list-tasks)."
    )
    task_src.add_argument(
        "--task-spec",
        metavar="TARGET:CLASS",
        help="Bring-your-own task: a dotted 'module:Class' or '/path/to/file.py:Class'. "
        "Imported and run in the harness process (keep it torch-free). "
        "Alternative to --task; lets a task live outside this repo.",
    )
    parser.add_argument(
        "--sut",
        help='SUT launch command, e.g. "python -m constructive.clbench_main".',
    )
    parser.add_argument(
        "--reset-every",
        type=int,
        action="append",
        default=[],
        metavar="N",
        help="Add a stateful arm that hard-resets every N instances (repeatable). "
        "Measured k is plotted. Default: 1, 2, 3 if no --reset-every/--reset-at given.",
    )
    parser.add_argument(
        "--reset-at",
        action="append",
        default=[],
        metavar="O1,O2,...",
        help="Add a stateful arm that hard-resets after exactly the listed 1-based "
        "completed-instance ordinals (ExplicitBoundaries; repeatable). Two main uses: "
        "(1) place resets on vs just-off a concept-drift boundary, e.g. "
        '--reset-at "30,60" --reset-at "35,65" on the BSM default schedule (drifts at '
        "30 and 60); (2) the phased store-removal protocol — reset once at the "
        'train/probe boundary, e.g. --reset-at "10", to measure what migrated into '
        "weights after the store is removed (see docs/phased-store-removal.md).",
    )
    parser.add_argument(
        "--task-kwarg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Task constructor kwarg (repeatable), e.g. variant=five_ch_wide.",
    )
    parser.add_argument(
        "--extra-pythonpath",
        action="append",
        default=[],
        metavar="DIR",
        help="Dir prepended to the SUT's PYTHONPATH (repeatable), e.g. suts/constructive.",
    )
    parser.add_argument("--name", default=None, help="System label for the curve (default: task name).")
    parser.add_argument(
        "--stderr-log",
        default="sut-stderr.log",
        metavar="FILENAME",
        help="Filename (relative to each arm's per-arm state dir) that captures the SUT's "
        "stderr, so a crashing SUT's diagnostics survive instead of being DEVNULL'd. On by "
        "default; pass an empty string to disable and let stderr fall through to DEVNULL.",
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="Per-response timeout (s).")
    parser.add_argument("--epsilon", type=float, default=EPSILON, help="Band-exclusion threshold.")
    parser.add_argument("--list-tasks", action="store_true", help="List available task names and exit.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list_tasks:
        print("\n".join(sorted(list_tasks())))
        return 0
    if not args.task and not args.task_spec:
        parser.error("one of the arguments --task or --task-spec is required")
    if not args.sut:
        parser.error("the following arguments are required: --sut")

    if args.task_spec:
        try:
            task_cls = load_task_spec(args.task_spec)
        except (ValueError, FileNotFoundError, ImportError, AttributeError, TypeError) as exc:
            parser.error(str(exc))
        task_label = args.task_spec.rpartition(":")[2]
    else:
        task_cls = get_task_class(args.task)
        task_label = args.task
    task_kwargs = _parse_kwargs(args.task_kwarg)
    command = shlex.split(args.sut)
    extra_pythonpath = [Path(p).resolve() for p in args.extra_pythonpath]
    name = args.name or task_label
    schedules: list[ResetSchedule] = [EveryNInstances(n) for n in args.reset_every]
    for spec in args.reset_at:
        ordinals = [int(tok) for tok in spec.split(",") if tok.strip()]
        if not ordinals:
            raise SystemExit(f"--reset-at needs at least one ordinal, got {spec!r}")
        schedules.append(ExplicitBoundaries(ordinals))
    if not schedules:  # neither flag given: keep the historical default sweep.
        schedules = [EveryNInstances(n) for n in (1, 2, 3)]

    def make_system(state_dir: Path, schedule: ResetSchedule, wipe: bool) -> SubprocessSystem:
        return SubprocessSystem(
            command,
            state_dir,
            reset_schedule=schedule,
            wipe_on_reset=wipe,
            name=name,
            timeout_s=args.timeout,
            extra_pythonpath=extra_pythonpath or None,
            stderr_log=(state_dir / args.stderr_log) if args.stderr_log else None,
        )

    def make_task() -> ContinualLearningTask:
        return task_cls(**task_kwargs)

    curve = run_reset_sweep(make_system, make_task, schedules, system_name=name, epsilon=args.epsilon)
    print(render_curve(curve))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
