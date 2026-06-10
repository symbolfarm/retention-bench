# Releasing retention-bench

This repo uses a **two-branch model** to keep a clean public face while the full
working history stays available:

- **`dev`** — the working branch. Everything lives here: code, tests, docs, plus
  the build process (`.tasks/`, `TASKS.md`, `AGENTS.md`, `feedback/`, `history/`,
  `scratch/`, this `RELEASING.md`, and `scripts/`). This is where **all** work and
  **all edits to public files** happen.
- **`main`** — the public face. An **orphan branch** (its own root commit, *no
  shared history with `dev`*), so nothing internal is reachable from `main`'s
  `git log`. `main` is a strict **path-subset** of `dev`: it contains only the
  paths listed in [`PUBLIC_PATHS`](PUBLIC_PATHS), minus the excludes.

There are **no `main`-only files**. The README, LICENSE, NOTICE, etc. are authored
on `dev` and snapshotted to `main`. **Never hand-edit `main`** — your change would
be overwritten by the next snapshot. Edit on `dev`, then promote.

## Why orphan, not a shared-history branch

A normal branch shares ancestry, so `git log main` would still expose every
internal commit. An orphan branch has a disjoint history, so the separation is
*structural*, not a matter of discipline. The trade-off: you can't `merge`
between `dev` and `main` (disjoint histories don't merge cleanly) — which is the
point. Promotion is a **snapshot**, never a merge: merging would drag the mess up.

## The promote script

[`scripts/promote.sh`](scripts/promote.sh) does the snapshot. It clears the target
tree and re-extracts exactly the `PUBLIC_PATHS` whitelist from `dev` — clearing
first so that **deletions on `dev` propagate** (a plain `git checkout dev -- <p>`
never removes files). It verifies no dev-only path leaked, and it **never pushes**.

```bash
# Validate mechanics without touching main (builds the snapshot in a temp worktree):
scripts/promote.sh dryrun

# First public release — create the orphan `main`:
scripts/promote.sh cut            # refuses if `main` already exists
scripts/promote.sh cut --force    # replace an existing `main` with a fresh orphan

# Subsequent releases — add a new snapshot commit onto the existing `main`:
scripts/promote.sh release
```

Source ref defaults to `dev`; override with `SRC=<ref> scripts/promote.sh ...`.

## Release checklist

1. Land all intended changes on `dev` (incl. README/LICENSE/docs edits).
2. `scripts/promote.sh dryrun` — confirm the tree is what you expect and the leak
   check passes.
3. `scripts/promote.sh cut` (first time) or `release` (after).
4. Review `main`: `git ls-files`, `git log`, and ideally `pytest` from a clean
   checkout — the public tree must actually run on its own.
5. Push when satisfied: `git push origin main`. Flipping repo visibility to public
   is a manual GitHub step. The script never does either for you.

## What stays on `dev` only

`feedback/`, `history/`, `scratch/` (incl. any author-outreach drafts), `.tasks/`,
`TASKS.md`, `AGENTS.md`, `scripts/`, `PUBLIC_PATHS`, `RELEASING.md`, and
`docs/archive/` (superseded pre-pivot specs). To change the public surface, edit
`PUBLIC_PATHS` — it is the single source of truth for what is public.
