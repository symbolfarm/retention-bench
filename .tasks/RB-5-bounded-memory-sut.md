# RB-5 Bounded-memory reference SUT — the partial-retention rung

**Priority:** high
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `suts/bounded_memory/**`, `tests/test_bounded_memory_clbench.py`

## Context

See [[RB-4]] for the full framing: retention-bench's reference set is all-or-
nothing retainers, so we can't draw the value figure (a *reference ladder* of
retention curves). RB-4 adds the floor; this task adds the **middle rung** — a
SUT that retains *partially*, proving the benchmark measures the **degree** of
retention, not just present/absent. This is the most persuasive single curve in
the ladder: it sits between the [[RB-4]] floor and the full retainers
(`associative_memory` / `bsm_accumulator`).

Part of the pre-C17 decoupling (publish the measurement infra as a methods
artifact, separate from the open-ended learned-constructive-SUT research).

## Goal

A keyless `bounded_memory` reference SUT that answers the
`symbolic_associative_retention` protocol but persists only a **capped, FIFO
window** of the most recent facts to the survive-dir. Facts that have been
evicted (older than the cap) fail recall, so retention is partial: its gain curve
sits visibly between the RB-4 floor and the full-retainer ceiling, and degrades
as the number of trained facts exceeds the cap.

## Acceptance criteria

- [ ] `suts/bounded_memory/` exists, mirroring `suts/associative_memory/`:
      package `bounded_memory/` with `__init__.py` + `clbench_main.py`,
      `pyproject.toml`, `sut-manifest.json`, `README.md`.
- [ ] `clbench_main.py` persists to the survive-dir like `associative_memory`, but
      enforces a FIFO cap of `N` entries (atomic write, same as the template).
      `N` is a small default (start at **8**) overridable via an env var
      (e.g. `BOUNDED_MEMORY_CAP`); document the default + override.
- [ ] Across resets, recall succeeds for facts still within the window and fails
      for evicted ones — partial retention, *not* the floor and *not* full.
- [ ] Runs keyless/offline through gain_curve, e.g.:
      ```
      .venv/bin/python -m retention_bench.gain_curve \
        --task symbolic_associative_retention \
        --sut "python -m bounded_memory.clbench_main" \
        --extra-pythonpath suts/bounded_memory \
        --reset-every 1 --reset-every 2 --name bounded-memory-partial
      ```
- [ ] Debrief records actual P/C/R(k) and confirms the curve lands strictly
      between the RB-4 floor and a full retainer on the same task (sanity-check by
      running `associative_memory` for the ceiling).
- [ ] `tests/test_bounded_memory_clbench.py` drives the SUT through
      `SubprocessSystem` (model on `tests/test_associative_memory_clbench.py`) and
      asserts eviction: a fact trained beyond the cap is forgotten while a recent
      one survives a reset.
- [ ] Full suite green: `.venv/bin/python -m pytest`.
- [ ] `scripts/promote.sh dryrun` clean.

## Relevant files

- `suts/associative_memory/` — template (it already persists to the survive-dir;
  the only addition is FIFO eviction at the cap).
- `tests/test_associative_memory_clbench.py` — test template.
- `retention_bench/gain_curve.py` — driver.
- `harness/dir_lifecycle.py` — DIR lifecycle (read-only).

## Decisions already made

- **Target task: `symbolic_associative_retention`** — same as RB-4, so all three
  rungs (floor / partial / full) plot on one figure.
- **Mechanism: FIFO eviction at a small cap (default 8), env-overridable.** A cap
  is the simplest knob that produces a curve *between* floor and ceiling and makes
  "degree of retention" legible. The cap must be small enough that the standard
  `symbolic_associative_retention` fact count exceeds it — verify against the
  task's actual fact count and note it in the debrief; adjust the default if 8
  doesn't produce visible eviction.
- **Keyless/offline**, modeled on `associative_memory`.

## Out of scope

- The reference-ladder **figure** + README/`run.sh` reference-SUT-list edits —
  consolidation step (RB-6), depends on this + [[RB-4]]. Keep edits inside
  `suts/bounded_memory/**` + `tests/test_bounded_memory_clbench.py`.
- Any container/Dockerfile.
- Tunable eviction policies beyond FIFO (LRU etc.) — FIFO is enough for the rung.
