# C6 Constructive-friendly task with an understanding-vs-stenography reward

**Priority:** medium
**Blocked by:** C1
**Touches:** `retention_bench/tasks/`

## Context

CL-Bench's reward-tasks measure task-reward improvement (closer to plasticity)
and don't natively separate shallow recall from deep understanding — the exact
signal Toby's research frame cares about ([[project_toby_research_frame]]). If C1
triage finds none of their six tasks preserve this, we contribute one. This is
where our retired by-`question_type` breakdown (surface_factual vs multi_hop) is
re-expressed as a reward decomposition.

## Goal

A CL-Bench-format task with exploitable latent structure that (a) requires state
across hard resets and (b) whose reward decomposes into a shallow-recall vs
deep-adaptation component.

## Acceptance criteria

- [ ] Implements `ContinualLearningTask` (single-shot instances; `r_max` set).
- [ ] Reward separates a stenography-style component from an
      understanding/transfer component.
- [ ] Runs end-to-end with the C2 system + constructive SUT; the two reward
      components diverge between a memorizing and a generalizing system.

## Relevant files

- `/home/agent/src/cl-bench/src/tasks/` (format reference)
- C1 triage doc (justifies the gap)
- old `tasks/smoke-test/`, `scorer/aggregate.py` (by-type breakdown ideas)

## Decisions already made

- Only build this if C1 shows their tasks don't carry the understanding signal.

## Out of scope

Anything not about the task itself.
