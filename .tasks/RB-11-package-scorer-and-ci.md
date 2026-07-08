# RB-11 Package `scorer` correctly + add CI with a non-editable install check

**Priority:** high
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `pyproject.toml`, `scorer/` → `retention_bench/` (fold the band formula),
`retention_bench/gain_curve.py` + `scorer/__init__.py` + `tests/test_scorer_aggregate.py`
(import sites), new `.github/workflows/ci.yml`

## Context

Review 2026-07-07 finding 4, verified 2026-07-08: `pyproject.toml:43` includes only
`harness*` and `retention_bench*`, but `scorer` is imported from three places including the
**shipped** path `retention_bench/gain_curve.py:55` (the `retention-bench` console script's
module). A non-editable `pip install .` therefore produces a broken install;
`pip install -e .` only works because the editable path leaks the repo root. Separately, the
review (and both constructive-retention reviews) flagged that **there is no CI config in the
repo at all**, even though the suite skips cleanly without `cl-benchmark` — so a plain 3.13
job would be cheap and would catch exactly this packaging bug via a non-editable install step.

## Goal

The band formula ships in an installed package, and CI proves it on every push by installing
non-editably and running the suite.

## Acceptance criteria

- [ ] Fold `scorer/aggregate.py`'s 5-line band formula into `retention_bench` (e.g.
      `retention_bench/scoring.py`), keep `scorer` as a thin re-export shim (or drop it and
      update the three import sites). `retention-bench` console script imports resolve under a
      non-editable install.
- [ ] `pyproject.toml` package config no longer omits shipped code (either `scorer*` added to
      `include`, or the fold above makes it moot).
- [ ] `.github/workflows/ci.yml`: Python 3.13; `pip install .` (**non-editable**) as an
      explicit step so a future packaging regression fails CI; then run the suite (it skips
      cleanly without `cl-benchmark`, so no upstream dep needed for the green path).
- [ ] Docker-gated container tests stay separate / non-blocking (as today).

## Decisions already made

- **Fold rather than just add to `include`** is preferred (one fewer top-level package for a
  5-line formula), but adding `scorer*` to `include` is an acceptable minimal fix if the fold
  is disruptive. (Review 2026-07-07 finding 4.)

## Out of scope

- Running the full `cl-benchmark`-dependent suite in CI (3.13 + heavy dep) — the skip-clean
  path is enough to guard packaging + the pure-Python tests. A deps-installed job can come later.
