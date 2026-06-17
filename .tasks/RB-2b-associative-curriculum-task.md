# RB-2b Deterministic associative curriculum task

**Priority:** high
**Blocked by:** RB-2a
**Touches:** `retention_bench/`, `tests/`, `docs/`

## Context

RB-2a pins the first curriculum substrate as a deterministic symbolic
associative-retention task. The task should give constructive-retention a small,
non-frontier M2 target where the absent skill, retained structure, and held-out
transfer probes are explicit.

Unlike `blind_spectrum_monitoring`, this task is not intended as an external
validity target. It is a developmental substrate for tiny models: exact,
procedural, reproducible, and small enough that failures are interpretable.

## Goal

Implement the CL-Bench-compatible associative curriculum task with deterministic
instance generation, exact scoring, phase/component metadata, and unit tests.

## Acceptance criteria

- [ ] A `ContinualLearningTask` is available to Retention Bench / CL-Bench under
      the task name pinned by RB-2a.
- [ ] The task is single-shot per instance: one `Query`, one structured response,
      one `InstanceOutcome`.
- [ ] Instances include train/context, memorization probe, and transfer probe
      phases as specified by RB-2a.
- [ ] Each outcome metadata records at least `phase`, `component`, `concept_id`,
      `expected`, `exposure_index`, and `probe_after_exposures`.
- [ ] Scoring is exact and deterministic, with only the normalization specified
      by RB-2a.
- [ ] `TaskResult.metrics` reports aggregate probe performance and separate
      memorization vs transfer metrics.
- [ ] Tests cover task determinism, schema validation / invalid responses,
      exact scoring, and component metric reporting.

## Relevant files

- `retention_bench/`
- `tests/`
- `/home/agent/src/cl-bench/src/interface.py`
- `/home/agent/src/cl-bench/src/tasks/`

## Decisions already made

- The first implementation should not depend on LLM judges or frontier-agent
  competence.
- The first implementation should include exposure metadata even though it runs
  in one-shot mode initially.
- Multi-step agentic task support remains C8, not part of this task.

## Out of scope

- Reference SUT and gain-curve smoke; handled by RB-2c.
- Repeated-exposure schedules and sample-efficiency curves; handled by RB-3.
- Constructive-retention model changes.
