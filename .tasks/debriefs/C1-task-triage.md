# Debrief: C1 Triage CL-Bench's tasks for cross-reset purity, shape, and the understanding signal

**Completed:** 2026-06-07
**Commit:** b9826a7

## What shipped

`docs/clbench-task-triage.md`: scores all six CL-Bench tasks
(blind_spectrum_monitoring, codebase_adaptation, cohort_studies,
database_exploration, exploitable_poker, sales_prediction) on the three
required axes — cross-reset purity, single-shot-vs-multi-step shape, and
understanding-vs-stenography — in a comparison table, with a first-target
recommendation, a "no new task needed" conclusion, and the list of tasks
that need the SUT contract extended to in-instance turns.

**Recommendation: blind_spectrum_monitoring first.** It is the *only*
single-shot task (verified directly in `task.py:710` + `_advance`), so it
runs through CL-Bench's runner against our existing single-shot SUT contract
with zero extension — and it is independently strong on cross-reset purity
(accumulated latent occupancy map drives IoU reward) and the understanding
signal (must infer hidden persistent structure from noisy scans, not
transcribe). Also a good constructive-learner fit.

## Descoped / deferred

Nothing descoped — analysis-only task, all acceptance criteria met. Building
the adapter (C2) and any new task (C6) were explicitly out of scope.

## Design decisions

- **Treated "the only single-shot task" as decisive but verified the other
  axes anyway.** Shape alone forces blind_spectrum (everything else loops
  `step()`), but I confirmed it's also high on purity + understanding so the
  pick isn't merely "least-bad fit." If it had been single-shot *and* weak on
  retention signal, the honest call would have been to flag a C6 gap.
- **Named exploitable_poker as the second target** (not asked for, but the
  brief's "notes which tasks need the contract extended" invited ordering
  them). Rationale in the doc: highest cross-reset purity of the multi-step
  set, clean continuous reward, deterministic opponent, no Docker.
- **De-prioritized database_exploration on the understanding axis** — its
  reward is efficiency-only (a wiped system stays *correct*, just slower), so
  a schema notepad scores well. Most stenography-friendly of the six; worth
  recording so a future agent doesn't pick it for an understanding-transfer
  showcase.

## Observations

- **The framework already gives us the cross-reset-purity metric for free.**
  `interface.py` documents `mean_gain` = stateful − stateless baseline reward.
  That *is* axis (a): a task with high gain has a load-bearing retention
  signal. We don't need to invent a purity measure — reuse theirs.
- **Concept drift makes the retention curve non-monotonic** (carried into the
  doc as a C3/C4 note). blind_spectrum injects drift via schedule-stage
  transitions; a reset landing on a drift boundary can *help* (clears stale
  belief) while a mid-stage reset purely hurts. C2's explicit-boundary reset
  schedule should let C4 place resets on/off drift boundaries deliberately to
  expose this — it's a richer story than "more memory = better," and directly
  exercises the C2 acceptance criterion for an explicit-boundary-list schedule.
- **All five non-spectrum tasks are multi-step**, confirming the pivot-plan §3
  risk concretely: targeting any of them is gated on a multi-step SUT adapter
  loop (not a contract change — the JSONL channel already supports N
  round-trips). Useful scoping fact for whenever we move past task #1.

## Follow-ups

### Considered and dropped

- *File a "multi-step SUT adapter" task now.* Dropped — premature. It's only
  needed when we move to target #2 (poker), which is well past C3/C4. The
  triage doc records the requirement; filing a task now would just age in the
  queue. Re-raise after C4 if we commit to a second task.
