# C1 Triage CL-Bench's tasks for cross-reset purity, shape, and the understanding signal

**Priority:** high
**Blocked by:** nothing
**Touches:** `docs/clbench-task-triage.md`

## Context

We're building on Continual Learning Bench (see `docs/clbench-pivot-plan.md`).
CL-Bench ships six tasks (blind_spectrum_monitoring, codebase_adaptation,
cohort_studies, database_exploration, exploitable_poker, sales_prediction). We
need to pick the first task to target with our constructive + hard-reset system.
Two of their tasks are multi-step *agentic* (poker, DB exploration); our SUT
contract is single-shot per instance (C0 spike confirmed the runner supports
multi-step, but our SUTs answer once). So shape matters.

## Goal

A short triage doc that picks the first target task (or concludes we need a new
one — feeds C6), scoring each CL-Bench task on three axes.

## Acceptance criteria

- [ ] `docs/clbench-task-triage.md` scores all six tasks on: (a) **cross-reset
      purity** — does reward require state carried across instances (so a hard
      reset is meaningful)? (b) **shape** — single-shot vs multi-step-agentic per
      instance. (c) **understanding-vs-stenography** — can the reward distinguish
      shallow recall from deep adaptation (the signal from
      [[project_toby_research_frame]])?
- [ ] A first-target recommendation with rationale, or a "build new" conclusion.
- [ ] Notes which tasks need the SUT contract extended to in-instance turns.

## Relevant files

- `/home/agent/src/cl-bench/src/tasks/*/task.py` (their task implementations)
- `/home/agent/src/cl-bench/src/tasks/*/README.md`
- `docs/clbench-pivot-plan.md`

## Decisions already made

- We adopt their harness; we do not port their tasks into our format.
- D2 (resolved 2026-06-07): pick from their six after triage rather than
  building a constructive-friendly task up front — unless triage shows none fit.

## Out of scope

Building the adapter (C2) or any new task (C6). This is analysis only.
