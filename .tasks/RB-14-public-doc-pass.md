# RB-14 Public-facing doc pass (codenames, dangling refs, dev paths, metric status)

**Priority:** medium
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `docs/` (esp. `metrics.md`, `sut-interface.md`), shipped docstrings across
`harness/`/`retention_bench/`/`suts/`, `retention_bench/_clbench.py`, the development brief

## Context

Review 2026-07-07 (Architecture gripe 1, Docs §1–3). The repo reads as a public v0.1 but
carries internal-pivot residue that an external reader follows *despite*, not because of:

- **Pivot codenames** (C0, C2, C9, C10, C20, B4a, B13, RB-2b/c …) pervade docstrings and docs
  and reference `.tasks/` debriefs / archived docs not on the public branch.
- **Dangling references:** `docs/clbench-pivot-plan.md`, `docs/clbench-task-triage.md`,
  `docs/trace-schema.md`, `docs/task-definition-schema.md`, and `.tasks/` are cited from
  shipped docstrings + the brief but don't exist on this branch (archived by C18).
- **Developer-machine residue:** `_clbench.py`'s import-error message tells users to run
  `/home/agent/src/cl-bench/.venv/bin/python` — a path from the original dev container.
- **Aspiration vs implementation isn't marked:** AURC, half-retention `k`, cold-start cost,
  wall-clock, and the shape classifier are presented in `metrics.md` as if reported, but none
  are computed → over-claiming risk.

## Goal

The docs and shipped strings read cleanly to an external reader with no access to the private
task history — the prerequisite polish for the orphan-`main` public cutover (C17).

## Acceptance criteria

- [ ] Pivot codenames swept out of shipped docstrings/docs into plain-language descriptions
      (the private `.tasks/` history keeps them; public surfaces don't).
- [ ] Dangling doc references fixed (repoint to archived/live locations or remove).
- [ ] `_clbench.py`'s error message points at a generic/relative interpreter path, not the dev
      container's.
- [ ] `metrics.md` marks each metric **specified / implemented** so nothing reads as reported
      when it isn't. Note the container-enforced-vs-subprocess kill path (post-RB-10) here too.

## Decisions already made

- **Land before C17** (the orphan public `main` cutover), so the first public snapshot is
  already clean rather than needing a follow-up scrub. (Sequencing agreed 2026-07-08.)

## Out of scope

- Rewriting the metric *designs* — RB-12 owns the variance/reset-window changes; this task
  only marks status and fixes references/paths.
- The actual C17 branch cutover.
