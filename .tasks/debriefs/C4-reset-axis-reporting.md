# Debrief: C4 Reset-axis (retention curve) reporting + gain reconciliation

**Completed:** 2026-06-07
**Commit:** af158d0

## What shipped

`retention_bench/gain_curve.py` — a SUT-agnostic driver that sweeps a
`SubprocessSystem` over hard-reset densities and renders retention/gain as a
function of the *measured* reset count `k`. This is the pivot's net-new axis;
CL-Bench's single `mean_gain` has no `k`-axis.

- **`run_reset_sweep(make_system, make_task, reset_schedules, ...)`** runs three
  kinds of arm, each from a *fresh* survive-dir: a ceiling `C` (`NoReset`, no
  wipe), a stateless prior `P` (`EveryNInstances(1)` + `wipe_on_reset=True`), and
  one stateful point `R(k)` per requested schedule. `k` is the measured
  `system.scheduled_resets`, points sorted by it.
- **Normalisation reuses `scorer.aggregate.normalised_retention` verbatim** —
  `norm_gain(k) = (R(k) − P) / max(C − P, ε)` — plus the `C ≈ P` band exclusion.
- **Reconciliation** is checkable on every point: `GainCurvePoint.clbench_mean_gain`
  comes straight from CL-Bench's own `build_benchmark_aggregate`
  (`final_cumulative_mean_gain`); our `R(k) − P` numerator equals it exactly
  because both arms play the identical instance set.
- **`render_curve`** prints a band header + per-`k` table.
- **CLI** `python -m retention_bench.gain_curve --task … --sut "…" --reset-every N`
  sweeps any SUT command + CL-Bench task (resolved via their registry).
- `_clbench` gained re-exports (`run_task`, `serialize_instance_outcome`,
  `build_benchmark_aggregate`, `get_task_class`, `list_tasks`) so the single
  `src.*` chokepoint discipline holds; `__init__` lazily re-exports the curve API.

`tests/test_gain_curve.py` — 6 tests driving the deterministic counter SUT
through the full sweep (band, measured-`k` axis, flat-at-ceiling perfect-retention
curve, the headline reconciliation, the excluded-band path, and a render smoke).
Docs: `docs/metrics.md` gained a *Reset-axis curve* section (formula +
reconciliation + CLI); the constructive SUT README gained a sweep pointer.

### Acceptance criteria

- ✅ Driver runs the C2 system at a sweep of `k` and collects per-instance rewards
  per `k` (`run_reset_sweep`; outcomes retained on each point).
- ✅ Aggregation produces gain-vs-`k` reusing the scorer's k-axis logic, rendered
  as a table (`render_curve`).
- ✅ Documented reconciliation: at the matching `k`, our number equals CL-Bench's
  gain on the same run — asserted per-point against their `build_benchmark_aggregate`
  and written up in `docs/metrics.md`.

## Descoped / deferred

- **Frozen-corpus / concept-drift schedule** (carried from C3's "for C4 to pick
  up"). The driver works on seed-driven variants (`five_ch_wide`); the `default`
  3-stage `mixed_grid_lifecycle` schedule still needs its frozen corpus on disk
  before `ExplicitBoundaries` can place resets on/off drift boundaries. The
  driver already accepts arbitrary schedules, so this is a *data* prerequisite,
  not a code one — filed as **C10** rather than blocking C4.
- **AURC / half-retention-`k` summary statistics** (`docs/metrics.md` lists them
  for the book-track curve). Not in the C4 acceptance criteria; the curve itself
  is the artifact. Easy to add later over `GainCurve.points`.
- **A `run.sh reset-curve` wrapper.** The CLI is the runnable driver; `run.sh` is
  book-track-shaped (sources `.env`, defaults to the no_state SUT). Wiring the
  pivot path into `run.sh` is a separate cleanup, not C4 scope.

## Design decisions

- **`k` = measured `scheduled_resets`, not nominal density (1/n).** The pivot
  plan and brief speak of "number of hard resets `k`"; the literal, observable
  count is the honest axis and is dense/monotonic. `--reset-every N` is the user
  knob; the resulting `k` is what's plotted (e.g. every-1 over 6 instances → k=5).
- **Driver owns the ceiling and prior runs** rather than relying on the caller to
  pass `NoReset` / a wipe arm. `C` and `P` are *definitional* (the band the curve
  normalises against), so the driver computes them; `reset_schedules` is only the
  stateful points to plot. Passing `NoReset` as a point still works (yields k=0).
- **Stateless baseline = `wipe_on_reset=True` + `EveryNInstances(1)`, not
  CL-Bench's `reset_between_instances=True`.** Their runner-driven baseline calls
  `system.reset()`, which for us is a hard bounce that *keeps* the survive-dir —
  i.e. not stateless. The wipe arm is the genuine stateless baseline (matches the
  C2 test that scores it at 1/N).
- **Reconciliation compares against CL-Bench's *own* function**
  (`build_benchmark_aggregate`), not a re-derivation, so the equality is a real
  cross-check of their implementation, not a tautology against our own arithmetic.
- **Counter SUT for the reconciliation test, not the constructive SUT.** The
  constructive SUT emits gibberish (C3), so its band is ~0 and rewards are noise —
  a flaky basis for an equality assertion. The counter is deterministic and has a
  genuine retention signal, making the reconciliation crisp. The constructive
  path is still exercised live (see Observations).
- **Module named `gain_curve`** (chosen with Toby over `reset_curve`, which read
  like a verb). Leads with the CL-Bench-reconciled framing the brief asks for
  ("gain-vs-k") and avoids the `retention_bench.retention_curve` stutter.

## Observations

- **The machinery is honest on real data.** Run live against the constructive SUT
  on `blind_spectrum_monitoring/five_ch_wide` (tiny-model env), the curve reports
  `band = −0.0125 → EXCLUDED` and `norm_gain = —` for every point, with
  `clbench_gain = R(k) − P = −0.0125`. That is exactly C3's documented negative
  result, now *surfaced on the axis* by the `C ≈ P` exclusion rather than asserted
  in prose — and the reconciliation identity holds even when the band is excluded.
- **Reconciliation is an arithmetic identity, so it's SUT-independent.** Mean of
  per-instance `(rollout − baseline)` = difference of run-means whenever the
  instance sets align (they always do — the task presents all instances
  regardless of resets; wiping only touches SUT state). The counter just makes it
  a *readable* assertion; the constructive run confirms it holds under noise too.
- **`import retention_bench` already requires cl-bench** (via `system` → `_clbench`),
  so the lazy `__getattr__` in `__init__` only defers the *scorer* import that
  `gain_curve` adds — it doesn't widen the base import's dependency surface.
- Full suite green on the cl-bench 3.13 venv: 105 passed, 1 skipped.

## Follow-ups

### Filed as tasks

- **C10** Frozen-corpus generation for the `mixed_grid_lifecycle` drift schedule —
  unblocks placing resets on/off concept-drift boundaries (the C1 non-monotonic
  retention story) via the `ExplicitBoundaries` schedule the driver already accepts.

### Considered and dropped

- *AURC / half-retention-`k` summary stats over `GainCurve`.* Real but small, and
  not load-bearing until there's a non-trivial (non-excluded, non-flat) curve to
  summarise — premature before C10/a retaining SUT. Re-raise when a curve with
  shape exists.
- *`run.sh reset-curve` wrapper.* The `python -m` CLI is already the runnable
  driver; a thin wrapper adds no capability and `run.sh` is book-track-shaped.
