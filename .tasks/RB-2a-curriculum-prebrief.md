# RB-2a Curriculum pre-brief and implementation spec

**Priority:** high
**Blocked by:** nothing
**Touches:** `.tasks/`, `TASKS.md`, `docs/`

## Context

RB-2 originally asked for the first Retention Bench-owned curriculum task for
constructive retention. A re-read showed that it was first-of-kind work and left
the central substrate choice open: associative retention, compositional
retention, or a tiny generated world model.

The chosen first target is associative retention because it is the smallest task
that can cleanly separate memorization from transfer without frontier-model or
natural-language competence. The task should also leave an explicit path toward
few-shot / reinforcement-learning-style repeated exposure experiments without
making the first implementation an RL benchmark.

## Goal

Write the implementation-ready spec for the first curriculum task: exact task
name, instance schema, phase schedule, scoring rules, component metrics,
reference SUT behavior, gain-curve smoke command, and follow-up task boundaries.

## Acceptance criteria

- [ ] The spec pins the first curriculum target as deterministic symbolic
      associative retention.
- [ ] It defines the CL-Bench task shape as single-shot per instance, with no
      C8-style multi-step feedback requirement.
- [ ] It defines task metadata fields for `phase`, `component`, `concept_id`,
      `exposure_index`, and `probe_after_exposures` so repeated-exposure and
      RL-style variants can be added later without rewriting the data model.
- [ ] It decides whether train/context instances are scored, and how probe-only
      memorization and transfer metrics are reported.
- [ ] It specifies the stateful JSON reference SUT and the expected retention
      band against the wiped stateless prior.
- [ ] It specifies the CLI smoke shape for `retention_bench.gain_curve`.
- [ ] It updates `TASKS.md` if the queue summary needs to point future agents to
      the split tasks.

## Relevant files

- `.tasks/RB-2b-associative-curriculum-task.md`
- `.tasks/RB-2c-curriculum-reference-sut.md`
- `.tasks/RB-3-repeated-exposure-curriculum.md`
- `TASKS.md`
- `/home/agent/src/cl-bench/src/interface.py`
- `retention_bench/gain_curve.py`
- `tests/test_subprocess_system.py`

## Decisions already made

- RB-2 is split before implementation rather than implemented as one broad task.
- The first curriculum target is associative retention, not compositional
  retention or a tiny world model.
- RB-2 remains one-shot / exact-scored; repeated exposure and reward-feedback
  work is filed separately as RB-3.
- The curriculum data model should include exposure metadata from day one.

## Out of scope

- Implementing the curriculum task.
- Implementing the reference SUT.
- Changing `gain_curve` semantics.
- Implementing true RL reward-feedback loops.
