# C2 Productionize SubprocessSystem + system-side reset schedule + compute accounting

**Priority:** high
**Blocked by:** nothing
**Touches:** `retention_bench/`, `pyproject.toml`, `tests/`

## Context

The C0 spike (`scratch/c0-spike/`) proved a `SubprocessSystem` wrapping our
`harness.sut_process` is driven by CL-Bench's real runner, and that a hard RESET
(SIGKILL + respawn, only the on-disk survive-dir persists) rides on their
existing `reset_between_instances` hook with no core change. Now make it real.

Key C0 finding: `reset_between_instances` is a *boolean* (resets after every
instance, k=1 density only). For a retention *curve* over `k` we control reset
density **system-side** — count `instance_complete` in `observe()` and
self-bounce the process on a chosen schedule, running with
`reset_between_instances=False`. No upstream change required.

## Goal

A `retention_bench` package (depends on `cl-benchmark`) exposing a production
`SubprocessSystem`: process lifecycle reused from `harness.sut_process`, a
configurable reset schedule, and compute `UsageEvent`s.

## Acceptance criteria

- [ ] `retention_bench/` package; `pyproject.toml` declares `cl-benchmark` dep,
      python `>=3.13`.
- [ ] `SubprocessSystem(ContinualLearningSystem)`: spawn/kill via
      `harness.sut_process`; `respond()` maps `Query` -> SUT stage I/O ->
      `query.response_schema`; `reset()` = hard process bounce keeping survive-dir.
- [ ] **Reset schedule**: configurable k-density via `observe()` self-bounce
      (every-N-instances and explicit-boundary-list both supported), independent
      of the runner's `reset_between_instances`.
- [ ] Emits `UsageEvent`s for compute: `call_type="compute"`, FLOPs + survive-dir
      storage-delta in `metadata` (storage-delta from `harness.dir_lifecycle`).
- [ ] Tests: adapter drives the echo/counter SUT through the real runner; asserts
      hard-kill count matches the schedule and survive-dir state persists.

## Relevant files

- `scratch/c0-spike/run_spike.py` (the proven prototype)
- `harness/sut_process.py`, `harness/dir_lifecycle.py` (reuse)
- `/home/agent/src/cl-bench/src/interface.py`, `src/usage.py`

## Decisions already made

- Reset density is owned system-side via `observe()`; no upstream PR is a
  blocker (C0 finding). A first-class reset schedule upstream is a C7 nice-to-have.
- D1 (resolved 2026-06-07): adopt their harness; reuse only sut_process +
  dir_lifecycle from the old harness.

## Out of scope

Wrapping the constructive SUT (C3); reset-axis reporting (C4).
