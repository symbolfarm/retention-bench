# Debrief: RB-12 Metric variance story + post-reset-window reward

**Completed:** 2026-07-19
**Commit:** 9fb5841

## What shipped

All four acceptance criteria:

- **Post-reset-window reward `W(m)`** — mean reward over the first `m`
  (default 3, `--window-m`) instances after each hard reset, pooled across the
  run's resets, windows truncated at the next reset / run end.
  `SubprocessSystem` now records `reset_ordinals` (1-based, `len ==
  scheduled_resets`) to anchor the windows. Reported raw and as `W_norm`, the
  band formula applied to *matched-ordinal* prior/ceiling means.
- **Percentile-bootstrap CIs** (`scoring.bootstrap_mean_ci` /
  `bootstrap_norm_gain_ci`) over the per-instance `outcomes`: `R(k)` per
  point, `norm_gain` per point (all three arms resampled independently), and
  `P`/`C` themselves. Stdlib `random`, deterministic seed, `B=1000` default,
  `--n-boot 0` disables. Rendered in the table; `--ci-level` for the level.
- **ε scales with `r_max`**: `scoring.band_epsilon(r_max)` = `EPSILON ×
  r_max`, applied by default in `run_reset_sweep` (reads `r_max` off the task
  *after* the run, so RB-13's per-schedule shadowing is honored). `--epsilon`
  remains an absolute override; full-range tasks (`r_max = 1`) are unchanged.
- **`docs/metrics.md`**: new `W(m)`/`W_norm` section (with the
  retained-vs-relearned interpretation rule), the bootstrap procedure (scoped
  honestly: within-run noise only, seeds still matter), the relative-ε rule,
  the k-counts-not-placement footnote, and an updated Reporting checklist.

24 new tests (18 offline unit in `tests/test_scoring.py`, 6 counter-SUT
integration with exact expectations in `tests/test_gain_curve.py`); suite at
135 passed + 2 docker-gated skips. `./run.sh smoke` exercises the new columns
end-to-end.

## Descoped / deferred

Nothing from the brief. (AURC/shape-classifier stay specified-not-implemented
per the brief's out-of-scope; RB-14 marks their status.)

## Design decisions

- **`W_norm` (matched-ordinal window normalisation) added beyond the brief.**
  The brief asked for the raw window mean; raw `W(m)` is diluted by any
  structurally-unscored instances that land in the window, so I also compute
  the prior/ceiling means over the *same run ordinals* and report
  `(W − P_w)/max(C_w − P_w, ε)`. Valid because all arms play the identical
  instance sequence — the same precondition the CL-Bench reconciliation
  already relies on. This is the number directly comparable to `norm_gain`.
- **Window truncation semantics:** a window ends at the next reset (the
  instance completed *at* the next reset's ordinal still belongs to the
  current window — the bounce fires after it completes); windows never
  overlap. At `every_1` density each window is a single instance.
- **`m` default = 3.** Small on purpose: the window wants the instances where
  retained state and relearning haven't yet converged; anything longer
  re-dilutes. At dense schedules truncation makes `m` moot anyway.
- **Bootstrap = stdlib `random`, percentile method.** No numpy/scipy import
  in the shipped package (scipy is only transitively present via
  cl-benchmark); B=1000 × ≤90 instances is trivial cost. Deterministic under
  `bootstrap_seed=0` — CIs are reproducible from the same outcomes.
- **`norm_gain` CI resamples all three arms independently**, so prior/ceiling
  uncertainty propagates (a band near ε gives an honestly wide, sometimes
  >1-straddling interval — visible in the BSM smoke run). The alternative
  (treating P and C as fixed) looked precise and would have been wrong.
- **ε: kept `EPSILON = 0.05` as the *relative* constant** rather than adding
  a second constant; `band_epsilon` produces the absolute value. `r_max` is
  read via `getattr(task, "r_max", 1.0)` so a bring-your-own `--task-spec`
  class without `r_max` degrades to the old absolute behavior.
- **`run_reset_sweep(epsilon=...)` default changed `EPSILON` → `None`**
  (= relative). Explicit callers (all existing tests) are unaffected.

## Observations

- **`Touches` was incomplete:** the brief listed `gain_curve.py` +
  `scoring`/aggregate + docs, but the window metric needs reset *positions*,
  not just the count, so `retention_bench/system.py` gained `reset_ordinals`
  (4 lines). Flagging per the Touches-mismatch rule; it's an additive,
  observability-only change in the same spirit as `scheduled_resets`.
- A first draft of the propagation unit test used `R = C` exactly — at which
  point `(R−P)/max(C−P, ε)` is 1.0 for *every* resampled prior and the CI
  legitimately collapses. Scale-invariance at the ceiling is worth remembering
  when writing variance tests against perfect-retention fixtures.
- BSM declares `r_max = 1.0`, so the smoke run's ε is unchanged; the relative
  rule only bites on schedule-compressed tasks like
  `symbolic_associative_retention` (16/26).

## Follow-ups

### Considered and dropped

- Bootstrap CI for `W_norm` itself — mechanical to add, but the window pools
  few instances at dense schedules and a CI over n≈3 samples would invite
  over-reading; revisit if RB-15's curves make W_norm load-bearing.
- A `--window-m` sweep report (W as a function of m) — YAGNI until a real SUT
  shows a relearning signature worth profiling.
