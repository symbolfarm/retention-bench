# RB-3 Repeated-exposure curriculum variant

**Priority:** medium
**Status:** paused
**Blocked by:** nothing
**Touches:** `retention_bench/`, `tests/`, `docs/`

## Context

RB-2 keeps the first curriculum task one-shot and exact-scored, but the same
substrate should support a second research dimension: how many training
repetitions are needed before recall and transfer become reliable?

This is adjacent to reinforcement learning but should start smaller. The first
step is not a reward-feedback policy loop; it is an exposure schedule and metrics
variant that measures sample efficiency under repeated train/probe events.

Paused 2026-06-17: keep this task as the right future direction, but wait until
constructive-retention SUT development has advanced enough that exposure-count
curves would measure something meaningful.

## Goal

Extend the associative curriculum into a repeated-exposure variant and report
recall/transfer performance as a function of exposure count.

## Acceptance criteria

- [ ] The task accepts schedule knobs such as `num_exposures` and
      `probe_after_exposures` without changing the one-shot default.
- [ ] The generated run can repeat train/context instances before recall and
      transfer probes while preserving deterministic ordering.
- [ ] Metrics include recall and transfer performance grouped by exposure count.
- [ ] Tests cover at least two exposure schedules and verify deterministic
      instance metadata.
- [ ] Docs explain the distinction between repeated-exposure sample efficiency
      and true RL reward-feedback learning.

## Relevant files

- `retention_bench/`
- `tests/`
- `docs/`

## Decisions already made

- RB-2 should leave exposure metadata in the data model from day one.
- True RL reward-feedback semantics should not be introduced until the repeated
  exposure path is measured and useful.

## Out of scope

- Multi-step agentic task support.
- Reward-feedback retry loops.
- Constructive-retention model training changes.
