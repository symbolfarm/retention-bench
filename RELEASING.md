# Releasing retention-bench

This repo has **one branch, `main`**, with the full working history, and cuts
releases as **annotated tags plus GitHub Releases**.

Everything is public: code, tests, docs, and the build process (`.tasks/`,
`TASKS.md`, `AGENTS.md`, `notebook/`, `feedback/`, `history/`). That is
deliberate. retention-bench is a research instrument, and its task queue,
debriefs and negative results are part of what makes the instrument
inspectable. There is no curated subset and no promotion step: the invariant is
not "these paths are safe to show" but **nothing in this repo is
unpublishable**.

A release is therefore not a different tree — it is a *name* for one commit on
`main`, so that a result can say which exact tree produced it.

## What a version means here

Versions track the **measurement contract**, not the code:

- **Patch** (`v0.1.1`) — fixes, docs, new reference SUTs. Numbers published
  against `v0.1.0` remain valid.
- **Minor** (`v0.2.0`) — new tasks or probe rungs, new drivers. Old numbers
  remain valid but the ladder is no longer the same ladder.
- **Anything that changes what an existing number means** — the retention
  formula, the reset semantics, task content or scoring — is at minimum a minor
  bump, and must say so in the release notes. Silently changing a metric under a
  fixed version is the one thing this process exists to prevent.

`version` in [`pyproject.toml`](pyproject.toml) is the source of truth; the tag
matches it with a `v` prefix.

## Cutting a release

1. **Land everything on `main`.** Ordinary changes go via PR or direct commit;
   either way the release is cut from `main`, never from a side branch.

2. **CI green on the release commit.** CI runs on every push and PR
   (`.github/workflows/ci.yml`): non-editable install, `.[dev]`, the editable
   `cl-benchmark` pin, then `pytest`.

3. **Reproduce from a clean checkout.** CI proves the tests pass; this proves a
   stranger following the README gets the committed numbers. In a scratch
   directory, outside your working clone:

   ```bash
   git clone https://github.com/symbolfarm/retention-bench && cd retention-bench
   python3.13 -m venv .venv && . .venv/bin/activate
   pip install -e .
   pip install -e "git+https://github.com/pgasawa/continual-learning-bench.git@9cc63c0f429048b843e8d43ac4f2b0ea4df13724#egg=cl-benchmark"
   ./run.sh smoke
   ./run.sh ladder
   ```

   The keyless ladder is deterministic: its output must match the table in
   [`docs/reference-ladder.md`](docs/reference-ladder.md) exactly. A mismatch
   blocks the release — either the docs are stale or the metric moved.

4. **Bump `version` in `pyproject.toml`** and commit, if it is not already at
   the version being released.

5. **Tag the release commit** with an annotated tag:

   ```bash
   git tag -a v0.1.0 -m "retention-bench v0.1.0"
   git push origin v0.1.0
   ```

6. **Cut the GitHub Release** from that tag. Notes should cover: what changed,
   whether any published number's meaning changed (see *What a version means*),
   the `cl-benchmark` pin, and the commands that reproduce the ladder.

7. **Anything that links to a result links to the tag**, not to `main`. `main`
   moves; the tag is what a reader can check.

## Reproducibility notes

- The `cl-benchmark` dependency is pinned to a **commit SHA** in
  `pyproject.toml`, and the same SHA appears in `README.md` and the CI workflow.
  All three move together, and the pin belongs in the release notes — the
  upstream repo is the one input a tag cannot freeze.
- The `cl-benchmark` pin **must be installed editable**; as a wheel it drops the
  task data files and every task construction fails. This is an upstream
  packaging gap, documented at the install step in CI.
- Keyless reference SUTs are deterministic and reproduce exactly. Anything
  model-backed is not: those results are dated, pinned to a model identifier,
  and reported separately rather than as part of the ladder.

## Before the first public release

One-time steps, not part of the recurring procedure:

- Repo visibility flip — a manual GitHub action, and **Toby's decision alone**.
  No agent performs it.
- Confirm the branch ruleset (no delete, no force push) is applied to `main`.
- Confirm no document describes a branch model the repo does not have.
