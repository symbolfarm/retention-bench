# C13 Public/internal split — orphan `main` + promote tooling

**Priority:** high
**Blocked by:** nothing
**Touches:** `scripts/promote.sh`, `PUBLIC_PATHS`, `RELEASING.md`, branch structure (`dev`)

## Context

retention-bench is being prepared for publication (a public-credibility artifact;
see [[project_cleval_dual_purpose]]). Decided with Toby (2026-06-10): keep a
two-branch model where the **public face lives on a lean `main`** and the **full
working mess lives on `dev`**, and enforce the separation *structurally* via an
**orphan `main`** (its own root commit, no shared ancestry with `dev`) so nothing
internal is ever reachable from `main`'s history.

Key design points settled in discussion:

- **Orphan, not shared-history.** `main` shares no commits with `dev`. This gives
  a clean `git log` on `main` for free — there is no separate "squash" step;
  orphaning *is* the clean-history move.
- **Promotion is a snapshot, never a merge.** Merging `dev → main` would drag the
  mess up and the unrelated histories don't merge cleanly anyway. Each release =
  check out `main`, extract the whitelisted paths from `dev`'s tip, handle the
  divergent README, commit (optionally a single commit per release).
- **`tasks/` (lowercase, the smoke-test benchmark asset) is PUBLIC; `.tasks/`
  (the work queue) is dev-only.** Don't confuse the two.

This task sets up the **tooling and `dev` branch only**. The real orphan-`main`
cutover happens **last**, in C17, after the content tasks (C14–C16) have made
`dev` publishable — so `main`'s first commit is already correct rather than a
stale pre-pivot README that immediately needs fix-commits stacked on it.

## Goal

`dev` exists with the full current state; a `scripts/promote.sh` + `PUBLIC_PATHS`
manifest + `RELEASING.md` define and document the snapshot-promotion workflow; the
orphan-snapshot mechanics are proven by a **dry run into a throwaway branch**. No
real `main` cutover yet.

## Cut line (the `PUBLIC_PATHS` whitelist)

**On `main` (public):**
`retention_bench/`, `harness/`, `suts/`, `scorer/`, `tests/`, `tasks/` (smoke-test
asset), `run.sh`, `pyproject.toml`, `.gitignore`, `README.md` (lean variant,
maintained directly on `main` — C14), `LICENSE` + `NOTICE` (C15), `.env.example`
(C14), `docs/` minus the dev-only archive (curated by C16).

**`dev`-only (excluded):**
`feedback/`, `history/`, `scratch/`, `.tasks/`, `TASKS.md`, `AGENTS.md`, and the
superseded standalone-era docs (C16 parks these under a dev-only `docs/archive/`).

## Acceptance criteria

- [ ] `dev` branch created from the current tip (full state preserved).
- [ ] `PUBLIC_PATHS` manifest committed, listing the whitelist above; supports an
      exclude for sub-paths under an included dir (e.g. `docs/archive/`).
- [ ] `scripts/promote.sh` snapshots `dev`'s whitelisted tree onto `main`:
      clears-then-extracts so **deletions on `dev` propagate** (a plain
      `git checkout dev -- <paths>` won't remove files); leaves the `main`-only
      README/LICENSE/NOTICE untouched; prints the resulting tree for review and
      does not auto-push.
- [ ] Dry run: orphan-snapshot into a throwaway branch (e.g. `main-dryrun`) and
      confirm the tree contains **only** whitelisted paths — no `feedback/`,
      `history/`, `scratch/`, `.tasks/`, `TASKS.md`, `AGENTS.md`. Delete the
      throwaway branch after.
- [ ] `RELEASING.md` documents: the orphan model, the snapshot-not-merge rule,
      how to run a release, and the divergent-README caveat.

## Relevant files

- New: `scripts/promote.sh`, `PUBLIC_PATHS`, `RELEASING.md`.
- Reference: `.gitignore` (already excludes `runs/`, caches, `.env`).

## Decisions already made

- Orphan `main` (clean history), one repo, GitHub default branch will be `main`.
- Semi-public history is acceptable to Toby — we are *not* scrubbing `dev`'s past;
  the orphan only keeps the mess off `main`.
- Snapshot promotion, never merge. Cutover happens last (C17), not in this task.
- `tasks/` public vs `.tasks/` dev-only.

## Out of scope

- The actual orphan-`main` cutover / first release (C17).
- README/LICENSE/docs *content* (C14–C16) — this task only defines the machinery.
- Any history rewrite of `dev`.
