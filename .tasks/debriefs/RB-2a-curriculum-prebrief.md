# Debrief: RB-2a Curriculum pre-brief and implementation spec

**Completed:** 2026-06-17
**Commit:** 577d8e4

## What shipped

Wrote `docs/associative-curriculum.md`, the implementation spec for the first
Retention Bench-owned curriculum task. It pins the task name
`symbolic_associative_retention`, the single-shot CL-Bench shape, exact response
schema, deterministic associative curriculum, phase/component metadata, scoring
rules, reference SUT behavior, gain-curve smoke shape, and repeated-exposure
extension path.

Also linked the spec from `docs/README.md` and from the RB-2b/RB-2c child task
briefs.

## Descoped / deferred

No benchmark implementation landed in RB-2a. RB-2b owns the task implementation
and tests; RB-2c owns the reference SUT, gain-curve smoke, and docs that prove
the retention band; RB-3 owns repeated-exposure / sample-efficiency variants.

## Design decisions

- Chose symbolic associative retention as the first substrate because it is the
  smallest deterministic task that separates memorization from transfer without
  frontier-model competence.
- Kept RB-2 single-shot per CL-Bench instance. Multi-step feedback and agentic
  loops remain outside this path.
- Required `phase`, `component`, `concept_id`, `expected`, `exposure_index`, and
  `probe_after_exposures` metadata from day one so repeated-exposure and
  RL-adjacent variants can be additive.
- Decided train/context instances stay in the run stream but carry `reward=0.0`;
  probe-only metrics are the curriculum headline.
- Noted that CL-Bench only discovers tasks in its own `src/tasks/` tree, so RB-2b
  must add a Retention Bench local-task lookup path rather than modifying the
  pinned CL-Bench checkout.

## Observations

The main hidden implementation issue was task discovery. The current
`gain_curve` CLI calls CL-Bench's `get_task_class`, whose registry discovers only
upstream task modules. A local task fallback is required before the new task can
be runnable by name.

## Follow-ups

### Filed as tasks

- **RB-2b** Deterministic associative curriculum task — implement the task and
  exact-scored unit tests from the spec.
- **RB-2c** Curriculum reference SUT, gain-curve smoke, and docs — prove the new
  task has a hard-reset retention band.
- **RB-3** Repeated-exposure curriculum variant — measure recall/transfer as a
  function of exposure count after the one-shot substrate lands.
