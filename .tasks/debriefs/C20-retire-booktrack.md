# Debrief: C20 Retire the book-track — CL-Bench-native smoke is the only path

**Completed:** 2026-06-11
**Commit:** 12fe995 (work), C21 filing 2e27470

## What shipped

Path-2-only. The repo no longer straddles the book-track harness and the
CL-Bench extension:

- **`run.sh`**: `smoke` now `exec`s `python -m retention_bench.gain_curve` on
  `blind_spectrum_monitoring` (variant `five_ch_wide`) with the keyless
  `bsm_accumulator` SUT and a `--reset-every 1 2` sweep — offline, no API key.
  The fallthrough repoints to the same SUT-agnostic gain-curve driver.
- **Retired book-track code**: `harness/{event_loop,task_loader,trace_writer,__main__}.py`
  and `scorer/{exact_match,judge,curve,__main__,protocols}.py`. Kept the
  pivot-reused primitives: `harness/{sut_process,dir_lifecycle}.py`,
  `harness/stubs/echo_sut.py`, and `scorer/aggregate.py` **stripped** to just
  `EPSILON` + `normalised_retention` (rewrote `scorer/__init__.py` to match).
- **Dropped `no_state` + `naive_rag` SUTs** (per the brief decision); public
  reference set is now `bsm_accumulator` + `notes_llm` + `constructive`.
- **Tests**: deleted the 5 book-track files + the 4 dropped-SUT test files +
  `test_scorer_cli` (retired CLI) + `test_notes_llm_fake_openai` /
  `test_constructive_integration` (book-track `harness.__main__` drivers of kept
  SUTs). Trimmed `test_scorer_aggregate` to the band primitives and dropped the
  `_make_container_spec` block from `test_docker_launch`. Removed all 6
  now-orphaned `tests/fixtures/*` files. **63 passed.**
- **Docs**: re-archived `trace-schema.md` + `task-definition-schema.md` to
  `docs/archive/`; fixed cross-refs/reference-SUT lists in `README.md`,
  `docs/README.md`, `docs/sut-interface.md`; minimal honesty touch on
  `metrics.md`; `TASKS.md` book-track section moved from "superseded" to
  "retired".
- **`pyproject.toml`**: console script → `retention_bench.gain_curve:main`;
  PyYAML moved from runtime deps to the `dev` extra (test-only now); `no-state-sut`
  extra renamed `llm-sut`.

`./run.sh smoke` prints the P/C/R(k) curve offline (P=0.2222, C=0.3109,
band=0.0887 — matches C19). `scripts/promote.sh dryrun` clean, no leaks.

## Descoped / deferred

- **Full rewrite of `sut-interface.md` + `metrics.md`** to the `SubprocessSystem`
  contract — beyond C20's "fix cross-refs" scope. Filed as **C21** (and added to
  C17's `blocked_by`). Both docs carry a C20 note pointing at it.
- **Kept SUTs' book-track `__main__.py`** left in place: `notes_llm.clbench_main`
  imports helpers from `notes_llm.__main__`, so it's a live dependency, not dead
  code. Out of scope to untangle SUT internals.

## Design decisions

- **Stripped `scorer/aggregate.py` rather than keeping it whole** (brief said
  "keep `scorer/aggregate.py` (+ whatever it imports — check `protocols.py`)").
  The check showed `aggregate → protocols → exact_match` is reachable only via
  the book-track `aggregate_records` path, which `retention_bench` never calls
  (`gain_curve` imports only `EPSILON` + `normalised_retention`). So I severed
  the import and retired `protocols.py` + `exact_match.py` too — the cleanest
  realisation of "retire the book-track" rather than leaving a dead scoring stack.
- **Retired more tests than the brief's 5 + dropped-SUT files.** `test_scorer_cli`
  exercises the deleted `python -m scorer` CLI; `test_notes_llm_fake_openai` and
  `test_constructive_integration` drive **kept** SUTs through the deleted
  `harness.__main__`. Their CL-Bench-native coverage already exists in
  `test_notes_clbench` / `test_constructive_clbench`, so no coverage was lost.
- **Kept the fake-openai shim.** The brief flagged it ("notes_llm still uses it")
  — confirmed: `test_notes_clbench` drives `notes_llm.clbench_main` through
  `SubprocessSystem` with the shim (writing its own temp fixture), so the shim
  stays but the 6 committed `tests/fixtures/*.yaml` are orphaned and were removed.
- **PyYAML → `dev` extra, not deleted.** No shipped code imports YAML (the
  book-track task loader was the only runtime consumer), but the test shim +
  `test_notes_clbench` do — so it's a test dependency now.
- **Minimal `metrics.md` touch instead of leaving present-tense "book-track".**
  Reworded the two lines that presented the book-track as live; the structural
  reconciliation is C21.

## Observations

- **Docker daemon is now reachable in this dev container** (the in-container
  Docker → Sysbox decision landed), so `test_docker_round_trip` and the
  constructive-container test actually *run* (not skip) — hence "63 passed,
  0 skipped" vs C19's "1 skipped". Not a regression; the gating `skipif` still
  works, the daemon is just present.
- The docker-launch container primitives (`ContainerSpec`, `build_docker_argv`,
  `spawn_sut`, `host_path_for_mount`) live in `sut_process.py` (keep-set); only
  the thin `_make_container_spec` *glue* lived in book-track `event_loop.py`. The
  argv/teardown coverage survives in `test_docker_launch`.
- `scorer` is not in `[tool.setuptools.packages.find].include` (only `harness*`
  + `retention_bench*`) — it resolves via repo-root on `sys.path`/PYTHONPATH.
  Pre-existing (gain_curve already imported `scorer.aggregate`); left as-is.

## Follow-ups

### Filed as tasks

- **C21** Reconcile `sut-interface.md` + `metrics.md` to the `SubprocessSystem`
  contract — both were authored for the book-track and only got minimal C20
  coherence fixes; the SUT-building doc reads as a contract that no longer exists
  (public-credibility risk). Added to C17's `blocked_by`.

### Considered and dropped

- Deleting the kept SUTs' book-track `__main__.py` — not dead
  (`notes_llm.clbench_main` imports from it) and out of scope.
- Adding `scorer` to the package include — pre-existing, orthogonal to C20.
