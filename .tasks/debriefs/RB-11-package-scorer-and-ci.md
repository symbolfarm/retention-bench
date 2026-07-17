# Debrief: RB-11 Package `scorer` correctly + add CI with a non-editable install check

**Completed:** 2026-07-17
**Commit:** c80840e

## What shipped

- **Fold, not include:** the band formula (`EPSILON`, `normalised_retention`)
  moved from `scorer/aggregate.py` to a new `retention_bench/scoring.py`, so it
  ships inside the already-packaged `retention_bench` package.
  `retention_bench/gain_curve.py` now imports `from .scoring import …` (plus
  two docstring references updated), which makes the `retention-bench` console
  script resolve under a non-editable `pip install .`.
- **Shim:** `scorer/aggregate.py` is now a thin re-export of
  `retention_bench.scoring`, so the dev-tree import sites
  (`scorer/__init__.py`, `tests/test_scorer_aggregate.py`) work unchanged.
  `scorer` stays deliberately out of the packaged distribution.
- **CI:** new `.github/workflows/ci.yml` — single job on `ubuntu-latest`,
  Python 3.13 (`actions/setup-python@v5`), an explicit **non-editable**
  `pip install .` step (the regression guard for exactly this packaging bug),
  `pip install pytest`, then `pytest`. `cl-benchmark` is deliberately not
  installed (heavy, non-PyPI); the suite `importorskip`s past it, and the
  docker-gated container tests self-skip without a daemon, so the job stays
  green on the dep-free path.

Verification of the reviewer's broken case: fresh Python 3.13 scratch venv,
`pip install <worktree>` run from `/tmp` (cwd outside the repo), then
`from retention_bench.gain_curve import main` and `retention-bench --help`
both resolve, and `import scorer` correctly fails (shim is dev-tree only).
Full suite from the worktree via the shared 3.13 venv: **86 passed, 2 skipped**
(the two docker-gated tests, as today).

## Descoped / deferred

- A CI job with `cl-benchmark` installed (full-suite coverage) — explicitly out
  of scope per the brief; the skip-clean path guards packaging + pure-Python
  tests.
- Dropping the `scorer` shim entirely and updating the three import sites — the
  brief preferred the shim; removing it can ride along with a later cleanup
  (e.g. the RB-14 doc pass or a book-track-residue sweep).

## Design decisions

- **Local verification used `--no-deps` + local cl-bench checkout.** The
  end-to-end `pip install .` in this dev container stalled on the pinned
  git+https clone of `cl-benchmark` (200 MB+, slow network), so the scratch-venv
  install used `pip install --no-deps <worktree>` — which still exercises the
  full setuptools packaging path (`packages.find`, wheel build, console-script
  entry point), i.e. exactly the surface finding 4 is about — and then satisfied
  the runtime dep from the local `/home/agent/src/cl-bench` checkout (plus
  `pydantic`/`litellm` from PyPI) to prove the console script imports
  end-to-end. CI's `pip install .` (no `--no-deps`) will do the true pinned-dep
  install on GitHub's network.
- **CI triggers:** plain `on: push` + `on: pull_request` with no branch filter,
  so both `dev` and `main` (and any worktree branch pushed for review) get the
  packaging guard. Trivial to narrow later if noise becomes an issue.
- **pytest via `pip install pytest`** rather than `pip install .[dev]`: the
  `dev` extra also drags in PyYAML, which the fake-OpenAI shim tests need —
  those tests are cl-benchmark-gated anyway, so plain pytest keeps the job
  minimal. If a dep-installed job is added later, use `.[dev]` there.

## Observations

- The worktree had been created from the orphan public `main` snapshot
  (`5183639`) rather than `dev`, so `TASKS.md`, `.tasks/`, and the review doc
  were absent. Reset the branch pointer to `dev`'s tip (`356ee51`) before
  starting; no commits were lost (the branch had none of its own). Worth
  checking the worktree-creation path if this recurs for other subagents.
- `retention_bench/__init__.py` imports `system.py` → `_clbench.py` at package
  import, so **any** `retention_bench` import requires `cl-benchmark` — there
  is no dep-free import surface. Fine for the benchmark's purposes, but it
  means the CI job proves the install shape via pytest collection + the
  packaging step, not via importing the installed package (the pure tests
  import `retention_bench.scoring` through the repo-root path). A future
  lazy-import of `_clbench` would let CI also smoke-import the installed
  package; not worth it today.

## Follow-ups

### Considered and dropped

- Adding a CI badge to README — cosmetic, and README is RB-14's (public doc
  pass) territory; let it land there.
- Making `retention_bench.scoring` importable without cl-benchmark in CI via
  lazy `_clbench` imports — real benefit is marginal while the suite already
  guards the formula through the repo-root path; re-raise only if a dep-free
  consumer of the package appears.
