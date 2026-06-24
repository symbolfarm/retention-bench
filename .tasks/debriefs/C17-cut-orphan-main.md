# Debrief: C17 Cut orphan `main` — first public release

**Completed:** 2026-06-24 (staged + verified; the public push is Toby's host-side step)
**Commit:** `5183639` (the orphan `main` release commit; no `dev` work commit — the deliverable is the branch itself)

## What shipped

A fresh **orphan `main`** cut from `dev` via `scripts/promote.sh cut --force`, then
amended to a versioned release message. `dev` untouched (`0de2ab9`).

- `main` = single orphan commit `5183639` `release: retention-bench v0.1 — reset +
  constructive extension on CL-Bench`, no shared ancestry with `dev`.
- Tree is exactly the `PUBLIC_PATHS` whitelist: `retention_bench/ harness/ suts/
  scorer/ tests/ docs/ run.sh pyproject.toml .gitignore README.md LICENSE NOTICE
  .env.example`. No `.tasks/`, `AGENTS.md`, `TASKS.md`, `feedback/`, `history/`,
  `scratch/`, `scripts/`, `PUBLIC_PATHS`, `RELEASING.md`, or `docs/archive/`.
- Includes the full keyless reference ladder (`no_state`, `reset_lossy`,
  `bounded_memory`, `associative_memory`) + `docs/reference-ladder.md`.

## Verification (all green)

- Orphan confirmed: 1 commit, `git merge-base dev main` → none.
- Leak check: no dev-only paths on `main` (also `promote.sh dryrun` was clean pre-cut).
- Standalone run: `pytest` from a clean `main` git-worktree (imports resolved to the
  worktree, not the dev tree) → **78 passed, 2 skipped**.
- README coherence: every path the README links exists on `main`.

## Descoped / deferred

- **The public push + repo visibility flip is Toby's** (per the brief). Not done
  here — and can't be: SSH is host-only in this dev container (push auth is the
  cron-on-host key, never forwarded in). Host-side steps surfaced to Toby:
  `git push origin main --force` (rewrites `origin/main`, currently `bdc5821`),
  `git push origin dev`, then flip visibility on GitHub.

## Design decisions

- **`cut --force`, not a fresh `cut`.** A `main` already existed — but it was the
  repo's *original 101-commit development history* (still carrying `.tasks/`,
  `AGENTS.md`, etc.), the pre-publication-model default branch that `dev` was
  branched from (merge-base = old `main` tip `162336f`). C17's intent is precisely
  to replace that with the clean orphan, so `--force` is correct. **No history is
  lost**: every one of those 101 commits remains in `dev`'s history (dev descends
  from old main). Surfaced to Toby before forcing.
- **Versioned commit message** (amended from promote.sh's generic "public snapshot
  from dev") at Toby's request — it is the public face's only visible commit.
- **No `Co-Authored-By` trailer on the release commit** — kept clean to match the
  script-generated release-commit convention and because it is the project's
  public-facing release under Toby's name. (Deviates from the usual trailer habit;
  intentional for this one commit.)
- **Amended `main` via a throwaway git-worktree**, not `git checkout main` —
  switching the primary working tree to `main` would have deleted the dev-only
  tracked files (`.tasks/` etc.) from the working dir. Worktree keeps `dev`'s tree
  intact.

## Observations

- `origin/main` (`bdc5821`) and `origin/dev` (`baefba4`) both exist on the private
  remote; the push will force-rewrite `origin/main`. Expected under the orphan model
  and low-risk (repo private, history preserved in `dev`).

## Follow-ups

### Considered and dropped

- Pushing / flipping visibility from here — impossible (host-only SSH) and explicitly
  Toby's trigger.
