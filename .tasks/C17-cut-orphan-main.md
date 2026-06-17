# C17 Cut orphan `main` — first public release

**Priority:** medium
**Blocked by:** nothing (C13/C14/C15/C16/C20/C21 completed)
**Touches:** branch structure (`main`), uses `scripts/promote.sh`

## Context

The final step of the publication housekeeping. C13 built the promote tooling and
`dev` branch; C14–C16 made `dev`'s public surface correct (lean README + LICENSE +
curated docs). Now cut the **real orphan `main`** from the cleaned state so its
*first* commit is already publication-correct — the whole reason the cutover was
deferred to last (see C13 context / [[project_clbench_pivot]]).

This is the trigger-pulling task. Do it deliberately and verify before anything is
pushed public.

## Goal

A fresh orphan `main` whose single initial commit contains only the whitelisted
public tree (plus the `main`-only README/LICENSE/NOTICE), with `dev` retained
intact as the working branch. Ready for Toby to flip the repo public.

## Acceptance criteria

- [ ] `main` recreated as an **orphan** (no shared ancestry with `dev`) via the
      C13 flow; `dev` untouched and still holding full history.
- [ ] `main`'s tree contains only `PUBLIC_PATHS` content — verified: no
      `feedback/`, `history/`, `scratch/` (incl. the C5 outreach draft), `.tasks/`,
      `TASKS.md`, `AGENTS.md`, `docs/archive/`.
- [ ] `main` is coherent on its own: README quickstart references only files that
      exist on `main`; `LICENSE`/`NOTICE` present; `pytest` collects/passes from a
      clean checkout of `main` (the public tree must actually run).
- [ ] Initial commit message is clean (e.g. `release: retention-bench v0.1 —
      reset + constructive extension on CL-Bench`); history on `main` is just this
      commit (clean log).
- [ ] **STOP before pushing public.** Surface the final `main` tree + `git log` to
      Toby for sign-off; do not flip repo visibility or force-push `origin/main`
      without explicit go.

## Relevant files

- `scripts/promote.sh`, `PUBLIC_PATHS`, `RELEASING.md` (from C13).

## Decisions already made

- Cutover is last, after content is publishable (C13 sequencing decision).
- Orphan `main`, snapshot-not-merge, one repo with `dev` alongside.
- The actual public flip / push is **Toby's trigger**, gated on his review — this
  task gets everything ready and stops.

## Out of scope

- Pushing to `origin` / flipping repo visibility (Toby's call, post-review).
- Any `dev` history scrubbing (explicitly not doing this; semi-public history OK).
- The C5 author outreach (separate, Toby-owned).
