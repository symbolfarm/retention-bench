# Debrief: C13 Public/internal split — orphan `main` + promote tooling

**Completed:** 2026-06-10
**Commit:** 785a556 (tooling: 1957990 + 785a556; RELEASING wording: this housekeeping commit)

## What shipped

The publication two-branch model's machinery, on `dev`:

- **`dev` branch** created from the pre-cleanup tip (full working state preserved).
  `main` (local) left frozen until the C17 cutover.
- **`PUBLIC_PATHS`** — the single source of truth for what is public. Whitelist of
  pathspecs + `!`-prefixed excludes (`docs/archive/`). Key call recorded inline:
  `tasks/` (smoke-test asset) is public; `.tasks/` (work queue) is dev-only.
- **`scripts/promote.sh`** — snapshots the `PUBLIC_PATHS` subset of `dev` onto an
  orphan `main`. Modes: `dryrun` / `cut [--force]` / `release`. Reads only the
  source ref's *committed* tree, builds in a throwaway `git worktree`, verifies no
  dev-only path leaked, never pushes.
- **`RELEASING.md`** — documents the orphan model, snapshot-not-merge rule, the
  "edit public files on `dev`, never on `main`" rule, and the release checklist.
- **Dry run passed**: snapshot tree contained only whitelisted paths; leak check
  clean; caller working tree untouched.

## Descoped / deferred

- The real orphan-`main` cutover / first release is **C17** (deliberately last, so
  `main`'s first commit is publication-correct rather than the stale pre-pivot
  README). `cut`/`release` modes are written but not exercised end-to-end here.
- `LICENSE` / `NOTICE` / `.env.example` are whitelisted but don't exist yet
  (C14/C15); `promote.sh` skips missing whitelist entries with a note.

## Design decisions

- **No divergent files — `main` is a strict path-subset of `dev`.** Dropped the
  originally-briefed "`main`-only divergent README" idea during the implementer
  re-read (brief refined in `162336f`): `AGENTS.md` (dev-only) carries internal
  orientation, so the README needn't differ between branches. This makes
  `promote.sh` a plain whitelist extract with zero special-cased files.
- **All snapshot work happens in a throwaway `git worktree`, reading only the
  source ref's committed tree.** Chosen over operating in the caller's working
  tree (see Observations — the first approach deleted an untracked file). Invariant
  now guaranteed: the caller's tree is never touched and untracked/uncommitted
  files can neither leak into a snapshot nor be destroyed.
- **Orphan `main`, snapshot-not-merge, one repo.** Clean `main` log for free; the
  disjoint history means you *can't* merge `dev → main`, which is the point.

## Observations

- **The first `promote.sh` deleted the untracked C5 outreach draft during the dry
  run** (`scratch/c5-outreach-draft.md`, Toby's WIP). Two compounding defects:
  (1) `extract_whitelist` ended with `git add -A`, which staged the untracked
  draft (the leak check correctly flagged it); (2) the teardown `git checkout -f
  dev` then deleted the now-staged-then-orphaned file from disk. **Recovered
  byte-identical** from the dangling blob (`e7e892c`, verified by hash). The same
  `git checkout -f` also silently reverted an *uncommitted* fix to the script
  itself, which initially looked like a linter reverting my edit — it wasn't.
  Lesson banked: a release/snapshot tool must never operate in the user's working
  tree; build in an isolated worktree and read committed trees only.
- `git checkout <ref> -- <path>` already stages from the committed tree, so
  `git add -A` was never needed; removing it fixes both the leak and the deletion.
- The orphan dry-run leaves no ref behind (never committed) and the temp worktree
  is removed on `trap EXIT`, so repeated runs are clean.

## Follow-ups

### Considered and dropped

- *Refuse-to-run-on-dirty-tree guard* — moot once the tool stopped touching the
  caller's working tree at all; the worktree isolation supersedes it.
- *Pushing `dev`/recovering the diverged local `main`* — not C13's concern; C17
  recreates `main` as an orphan and Toby owns the push/visibility flip.
