# Debrief: RB-7 Reset-lossy reference SUT — the graded normalised rung

**Completed:** 2026-06-24
**Commit:** 08976bd

## What shipped

The graded normalised rung the RB-6 figure was missing — keyless, offline, deterministic:

- **`suts/reset_lossy/`** — package (`reset_lossy/clbench_main.py` + `__init__.py`),
  `pyproject.toml`, `sut-manifest.json`, `README.md`. Mirrors `associative_memory`'s
  persistence but answers a shrinking, reset-coupled fraction of its facts.
- **`tests/test_reset_lossy_clbench.py`** — drives the SUT through `SubprocessSystem`
  + `run_reset_sweep` with the rate pinned via `RESET_LOSSY_RATE`; asserts full-band
  ceiling, graded `0 < norm < 1` at every arm, and decay (every_1 < every_2) pinned
  to exact `R` values.
- **`./run.sh ladder`** — added a `reset-lossy-graded` rung between the floor and the
  retainers; reordered the comment to floor → graded → retainers.
- **`docs/reference-ladder.md`** — "four rungs" table (now with separate `R(k=12)` /
  `R(k=25)` columns since reset count now matters), both ASCII bars regenerated with
  `reset_lossy` at both reset arms, graded-axis framing, and the "Not yet on the
  ladder" note trimmed to just `notes_llm` / `constructive` (the reset-lossy gap is
  filled).
- **README** — added `reset_lossy` to the ladder bullet as the graded `0 < norm < 1`
  rung.

`suts/` and `tests/` are whitelisted wholesale in `PUBLIC_PATHS`, so all of this ships.

## Numbers (default rate 0.3, deterministic, from `./run.sh ladder`)

| arm | k | P | C | R(k) | norm `(R−P)/(C−P)` |
|---|---:|---:|---:|---:|---:|
| ceiling (no reset) | 0 | 0.000 | 0.615 | 0.615 | — |
| every_2 | 12 | 0.000 | 0.615 | 0.1538 (4/26) | **0.250** |
| every_1 | 25 | 0.000 | 0.615 | 0.0769 (2/26) | **0.125** |

- **Rate used:** 0.3 (default, `RESET_LOSSY_RATE`-overridable).
- **0 < norm < 1:** confirmed at both arms (0.250 and 0.125).
- **Decays with k:** confirmed — every_1 (k=25, R=0.077) sits strictly below
  every_2 (k=12, R=0.154). First reference SUT where reset *count* matters.
- **Reproducible:** fixed BLAKE2b hash + persisted load counter, no per-run
  randomness or seed file; re-runs reproduce exactly.

Full suite: **78 passed, 2 skipped**. `scripts/promote.sh dryrun` clean (leak check OK).

## Design decisions

- **`k` = resets survived via a persisted load counter.** The survive-dir holds a
  `load_count` bumped + persisted once per process start. The runner respawns the
  SUT lazily after each hard reset, so `k = load_count - 1` is exactly the resets the
  on-disk state has survived when a probe is answered. At k=0 the gate is wide open
  (full-band ceiling intact); the every_2 / every_1 sweeps produce load_count 13 / 26
  (verified by inspecting the persisted state).
- **`log2(1 + k)` exponent damping — deviation from the brief's raw `(1-rate)**k`,
  taken under the brief's explicit "equivalent deterministic scheme" allowance.** This
  task drives 12–25 hard resets *before* the probes run. Raw per-reset 0.3 compounding
  gives `0.7**12 ≈ 0.014`, below every fact's uniform `u`, so the literal formula
  wipes everything out and collapses the rung onto the floor (verified: R=0 at both
  arms before the change). Damping the exponent preserves the two properties the brief
  actually requires — strict monotone decay in `k` and full reproducibility — while
  landing the curve in the graded band the rung exists to populate. `rate` stays the
  per-reset loss knob. Documented in the module docstring, SUT README, and here.
- **Facts are never deleted from disk; only the answer gate moves.** Keeps the
  mechanism cleanly distinct from `bounded_memory`'s capacity eviction (reset-coupled
  loss vs a smaller box). The full fact set persists; the SUT just declines to answer
  the gated-out ones.
- **Transfer gated on the chain.** A transfer probe answers only if the object→attribute
  fact survives *and* its attribute→bin rule survives (each by its own `u`), matching
  the two-hop dependency.

## Follow-ups

### Filed as tasks
- None.

### Candidate (surfaced, not yet filed)
- **C17 narrative now has a genuinely graded normalised axis** (floor → leaky →
  retainers). The RB-6 debrief flagged that the metric only separated floor-vs-retainers;
  reset_lossy fixes that. Worth folding into the public writeup when C17 is cut.
- **A linear-in-k variant** (`rate` interpreted as total loss spread across the run's
  resets, no log damping) could be offered if a future task wants the per-reset rate to
  read literally against the observed reset count rather than via the log dampener.
  Dropped here to keep one clean, documented mechanism.
