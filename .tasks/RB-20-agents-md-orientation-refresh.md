# RB-20 Refresh AGENTS.md — two pivots stale

**Priority:** medium
**Blocked by:** —
**Touches:** `AGENTS.md`

## Context

Surfaced during RB-17 (README reframe). `AGENTS.md` is the first file a fresh agent is
told to read, and it predates both the **2026-06-07 CL-Bench pivot** and the
**2026-07-29 instrument reframe**. As written it actively misdirects:

- "What this repo is" calls the project "a research project designing a benchmark" —
  the framing RB-17 just removed from the public docs.
- `last_updated: 2026-05-20`; "Status" still says *scoping, late-stage* / *cleared for
  MVP implementation*, which is three phases behind reality (harness shipped, CL-Bench
  adapter shipped, native curriculum shipped, ladder re-measured).
- The read order points at documents that were archived or deleted:
  `docs/decisions-checklist.md`, `docs/tasks.md`, `docs/book-spec.md`,
  `docs/memory-targets-spec.md`, `docs/cohort-1-seeds.md`, `docs/validity.md`,
  `docs/protocol.md`, `docs/interface.md`, `docs/open-questions.md`,
  `docs/extensions.md`, `docs/topology.md`, `docs/worked-example-book-track.md`,
  `docs/question-set-spec.md`, and the whole `history/` tree.
- "Communication norms" mandates joint-scoping / echo-back mode and "do not start
  implementing on first contact" — appropriate during scoping, now wrong for a repo
  running a task-cycle execution queue.
- "What is not yet decided" and "What not to do without asking" are entirely
  book-track-era (cohort-1 novellas, two-leaderboard interface rewrite), all of which
  C20 retired.

## Goal

`AGENTS.md` orients a cold agent to the repo *as it is*: a research instrument extending
CL-Bench, with a live task-cycle queue, a real code layout, and a doc set whose entry
points are `README.md`, `docs/ROADMAP.md`, and `docs/README.md`.

## Acceptance criteria

- [ ] Framing matches RB-17 / `docs/ROADMAP.md`: research instrument / workbench, not a
      benchmark. No leaderboard or submission language.
- [ ] Status reflects the post-RB-16 reality, with a pointer to `TASKS.md` +
      `.tasks/LOG.jsonl` as the queue of record rather than an inline status narrative
      that will rot again.
- [ ] Every path referenced exists (check mechanically). Archived material is either
      dropped or clearly labelled as `docs/archive/`, dev-branch-only.
- [ ] Read order rewritten around the current entry points; the repo tour in
      `docs/README.md` is referenced rather than duplicated.
- [ ] Communication norms updated — joint-scoping/echo-back was a scoping-phase mode;
      state what actually applies now (task-cycle execution, ask before pushing `main`).
- [ ] "What not to do without asking" rewritten around live hazards: never hand-edit
      `main` (orphan snapshot, `scripts/promote.sh`), don't push host-side, don't
      co-edit the constructive-retention sibling repo.
- [ ] Sibling-project section kept — it is still accurate and load-bearing.

## Relevant files

- `AGENTS.md` — the file being rewritten
- `README.md`, `docs/ROADMAP.md`, `docs/README.md` — the framing and entry points it must match
- `TASKS.md` — current status text to align with

## Out of scope

- Any code change.
- Re-litigating the reframe (settled by RB-17).
