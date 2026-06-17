# Debrief: RB-1 Repair dev environment and task docs

**Completed:** 2026-06-17
**Commit:** 1c9f3fb

## What shipped

Restored the local Python 3.13 dev loop by reinstalling uv-managed CPython
3.13.13, recreating the missing editable CL-Bench checkout at
`/home/agent/src/cl-bench` on the pinned commit, and reinstalling CL-Bench plus
retention-bench into `.venv`.

Updated `run.sh` to prefer the repo-local `.venv/bin/python` when available,
with `RETENTION_BENCH_PYTHON` as an override. Updated `TASKS.md` so the current
focus reflects the completed C0-C4 pivot path, the live pending queue, and the
repo-local dev-loop interpreter.

## Descoped / deferred

No benchmark behavior or dependency pins changed. The repo-local `.venv` and the
external `/home/agent/src/cl-bench` checkout are environment state, not committed
artifacts.

## Design decisions

- Kept the CL-Bench checkout at `/home/agent/src/cl-bench` because the existing
  environment metadata already pointed there; changed the documented execution
  path to `.venv/bin/python` so routine commands are repo-local.
- Made `run.sh` choose `.venv/bin/python` automatically instead of requiring the
  caller to activate the venv. This keeps the canonical `./run.sh smoke` command
  truthful.

## Observations

- The broken `.venv` was caused by interpreter symlinks pointing at a missing
  uv-managed CPython install.
- CL-Bench was present only as stale editable metadata; the actual
  `/home/agent/src/cl-bench` source directory was absent.
- `uv pip install -e '.[dev,llm-sut]'` hung while updating the Git dependency,
  but a direct clone of the pinned CL-Bench repo followed by editable installs
  completed quickly.
- Verification passed:
  - `./run.sh smoke`
  - `.venv/bin/python -m pytest -q` (`50 passed, 1 skipped`)

## Follow-ups

### Considered and dropped

- Filing a separate task for the uv Git-dependency hang: dropped for now because
  the direct pinned checkout restored the dev loop, and this may be transient
  network/cache behavior rather than a repo issue.
