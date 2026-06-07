# C3 Constructive system end-to-end on the target task under hard reset

**Priority:** high
**Blocked by:** C1, C2
**Touches:** `retention_bench/`, `suts/constructive/`

## Context

`suts/constructive/` already exists (torch-CPU, grows capacity across READ/RESET,
checkpoints to DIR). CL-Bench explicitly excludes parametric methods and invites
them as community contributions — this is our headline contribution and the CNN
dependency ([[project_constructive_transformers]]).

## Goal

Run the constructive SUT as a CL-Bench system, via the C2 `SubprocessSystem`, on
the C1 target task, under a hard-reset schedule — producing real rewards.

## Acceptance criteria

- [ ] Constructive SUT runs through `SubprocessSystem` on the C1 target task.
- [ ] Its persistent state (weights/checkpoint) lives in the survive-dir and
      survives hard resets; a wiped run (stateless baseline) measurably differs.
- [ ] Compute `UsageEvent`s (FLOPs + storage-delta) populated; storage-delta ~0
      for in-place growth, FLOPs the load-bearing cost signal.
- [ ] A run on the C1 task completes and emits a `TaskResult` with non-trivial
      gain vs the stateless baseline (or a documented negative result).

## Relevant files

- `suts/constructive/constructive/{__main__,model,train,checkpoint}.py`
- `retention_bench/` (C2 adapter)
- C1 triage doc (target task choice)

## Decisions already made

- Constructive SUT keeps its existing process contract; the adapter bridges it.

## Out of scope

Reset-axis curve reporting (C4); a new task (C6).
