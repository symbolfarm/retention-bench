# RB-1 Repair dev environment and task docs

**Priority:** high
**Blocked by:** nothing
**Touches:** `.venv/`, `TASKS.md`, `.tasks/LOG.jsonl`

## Context

The initial workspace review found two immediate operational blockers:

- The documented CL-Bench Python path in `TASKS.md` points at
  `/home/agent/src/cl-bench/.venv/bin/python`, which is absent in this container.
- The repo-local `.venv` points at a missing uv-managed CPython 3.13 install, so
  `./run.sh smoke` and the CL-Bench-backed tests cannot run.
- `TASKS.md` still describes C1/C2 as the current unblocked work even though the
  log shows C1-C4 and later cleanup tasks completed.

## Goal

Restore the local development loop and update the task-orientation docs so a
fresh agent can run the canonical smoke and see the current queue.

## Acceptance criteria

- [ ] A Python 3.13 environment exists at the repo-local `.venv` and can import
      `src.interface` from CL-Bench.
- [ ] `./run.sh smoke` completes from `retention-bench`.
- [ ] `TASKS.md` names the repo-local `.venv/bin/python` dev-loop path and the
      actual current pending task set.
- [ ] The task-cycle log is updated and this task has a debrief.

## Out of scope

- Changing benchmark behavior or CL-Bench pins.
- Starting CR-1 in `constructive-retention`.
