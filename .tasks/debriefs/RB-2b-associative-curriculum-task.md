# Debrief: RB-2b Deterministic associative curriculum task

**Completed:** 2026-06-17
**Commit:** c912d0a

## What shipped

Implemented the Retention Bench-owned `symbolic_associative_retention` task under
`retention_bench/tasks/`. The task is single-shot per CL-Bench instance, teaches
deterministic nonce object attributes and attribute-to-bin rules, then scores
exact memorization and transfer probes with separate component metrics.

Added a local task lookup fallback in `retention_bench._clbench` so
`gain_curve --task symbolic_associative_retention` can resolve Retention
Bench-owned tasks without modifying the pinned CL-Bench checkout. Fixed
`gain_curve --list-tasks` so it works without requiring `--task` / `--sut`, and
covered it with tests.

## Descoped / deferred

The reference JSON-state SUT and end-to-end gain-curve smoke are still deferred
to RB-2c. Repeated-exposure schedules and sample-efficiency metrics remain RB-3.

## Design decisions

- Implemented local tasks as an in-package registry (`retention_bench.tasks`) and
  kept CL-Bench lookup first so upstream task names continue to behave exactly as
  before.
- Kept the response schema to one exact-scored string field:
  `AssociativeAnswer.answer`.
- Train/context turns remain in the run stream and carry zero reward. Probe-only
  metrics (`probe_mean_reward`, `memorization_mean_reward`,
  `transfer_mean_reward`) are the curriculum headline.
- The default schedule is 8 object facts, 2 attribute-to-bin rules, 8 recall
  probes, and 8 transfer probes. The task's default `r_max` is therefore `16/26`.

## Observations

`gain_curve --list-tasks` existed but was unusable because argparse required
`--task` and `--sut` before the flag could return. The local task registry made
that visible immediately.

## Follow-ups

### Filed as tasks

- **RB-2c** Curriculum reference SUT, gain-curve smoke, and docs — prove the new
  task has a hard-reset retention band.
- **RB-3** Repeated-exposure curriculum variant — add exposure-count schedules
  and sample-efficiency metrics after the one-shot substrate is smoke-tested.

### Drive-by cleanup landed

- `tests/test_constructive_container_clbench.py` now skips cleanly when the
  `docker` binary is absent instead of failing during test collection.
