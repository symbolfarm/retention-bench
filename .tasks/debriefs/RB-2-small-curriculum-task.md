# Debrief: RB-2 Small curriculum task for constructive retention

**Completed:** 2026-06-17
**Commit:** split commit

## What shipped

RB-2 was split before implementation into a pre-brief/spec task, a deterministic
associative curriculum implementation task, a reference-SUT/gain-curve/docs task,
and a repeated-exposure follow-up.

## Descoped / deferred

Implementation was deferred to the child tasks. This debrief records a task
split, not shipped benchmark code.

## Design decisions

- The first curriculum target is associative retention because it is the smallest
  deterministic substrate that separates memorization from transfer.
- RB-2 remains one-shot and exact-scored; repeated exposure is tracked as RB-3
  rather than folded into the initial implementation.
- The curriculum data model should include exposure metadata from the first
  implementation so sample-efficiency and RL-style variants are additive.

## Observations

The original RB-2 brief was directionally right but too broad for a first
implementation pass. It crossed task design, CL-Bench integration, reference SUT,
gain-curve smoke, docs, and a possible repeated-training research dimension.

## Follow-ups

### Filed as tasks

- **RB-2a** Curriculum pre-brief and implementation spec — pin the exact target,
  schema, metrics, and task boundaries before implementation.
- **RB-2b** Deterministic associative curriculum task — implement the
  CL-Bench-compatible task and unit tests.
- **RB-2c** Curriculum reference SUT, gain-curve smoke, and docs — prove the task
  has a retention band and document the substrate.
- **RB-3** Repeated-exposure curriculum variant — explore exposure-count /
  sample-efficiency curves after the first substrate lands.
