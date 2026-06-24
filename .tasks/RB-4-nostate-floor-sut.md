# RB-4 No-state (ephemeral) reference SUT — the retention floor

**Priority:** high
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `suts/no_state/**`, `tests/test_no_state_clbench.py`

## Context

retention-bench's public reference set (`bsm_accumulator`, `associative_memory`,
`notes_llm`, `constructive`) is **all retainers** — every shipped SUT retains
across the hard RESET. There is no non-retaining baseline, so we can't draw the
figure that demonstrates the benchmark's value: a *reference ladder* whose
retention curves visibly separate tiers from floor to full retention. This task
adds the **floor**.

The old `no_state` SUT (deleted in C20, commit `12fe995`) is **not** what we
want: it was a book-track, LLM-calling SUT that merely ignored the survive-dir —
it needed an API key and the retired `harness.__main__` driver. We want a
**keyless, offline** floor that runs through the current `SubprocessSystem` /
`gain_curve` path, so the validity figure is reproducible without credentials.

This is a decoupling step: the public C17 release (cut the orphan `main`) is being
separated from the open-ended learned-constructive-SUT research. The floor +
partial-retainer ([[RB-5]]) + a consolidation figure are the pre-C17 validity
artifact.

## Goal

A keyless `no_state` reference SUT that answers the
`symbolic_associative_retention` protocol using **only in-process memory** — it
never reads or writes the survive-dir (`RETENTION_BENCH_DIR`). Its gain curve
should show high recall at `k=0` (within-episode learning) collapsing to the
prior floor for `k>=1`, because every hard RESET (process kill) erases its
un-persisted state.

## Acceptance criteria

- [ ] `suts/no_state/` exists, mirroring `suts/associative_memory/` structure:
      package `no_state/` with `__init__.py` + `clbench_main.py`, `pyproject.toml`,
      `sut-manifest.json`, `README.md`.
- [ ] `clbench_main.py` keeps an in-RAM dict for the process lifetime and answers
      the same TRAIN/RECALL/TRANSFER protocol as `associative_memory`, but has
      **no** `_load_state`/`_save_state` and never touches `RETENTION_BENCH_DIR`.
- [ ] Runs keyless/offline through gain_curve, e.g.:
      ```
      .venv/bin/python -m retention_bench.gain_curve \
        --task symbolic_associative_retention \
        --sut "python -m no_state.clbench_main" \
        --extra-pythonpath suts/no_state \
        --reset-every 1 --reset-every 2 --name no-state-floor
      ```
- [ ] The produced curve demonstrates the floor: recall holds at `k=0` and drops
      to ~prior `P` for `k>=1` (record the actual P/C/R(k) numbers in the debrief).
- [ ] `tests/test_no_state_clbench.py` drives the SUT through `SubprocessSystem`
      (model on `tests/test_associative_memory_clbench.py`) and asserts the
      across-reset collapse.
- [ ] Full suite green: `.venv/bin/python -m pytest` (per
      [[project_retention_bench_package]]: use the repo `.venv`).
- [ ] `scripts/promote.sh dryrun` clean (no public-path leaks).

## Relevant files

- `suts/associative_memory/` — the template to copy/adapt (esp.
  `associative_memory/clbench_main.py`, `sut-manifest.json`, `pyproject.toml`).
- `tests/test_associative_memory_clbench.py` — test template.
- `retention_bench/gain_curve.py` — the driver; how `--extra-pythonpath` + the
  `--sut` command are launched.
- `harness/sut_process.py`, `harness/dir_lifecycle.py` — SubprocessSystem + DIR
  lifecycle (read-only; do not edit).

## Decisions already made

- **Target task: `symbolic_associative_retention`** — facts are discrete and
  countable, so floor/partial/full tiers are legible on the same task and figure.
- **Semantics: in-RAM only (ephemeral), not truly-stateless.** Keeping
  within-process memory makes the curve *drop* from R(0) to floor, which visually
  demonstrates "the hard RESET erases working state" — more informative than a
  flat line. Document this choice in the README + debrief.
- **Keyless/offline**, modeled on `associative_memory`, not restored from the
  C20-deleted LLM `no_state`.

## Out of scope

- The reference-ladder **figure** and any README/`run.sh` reference-SUT-list
  edits — those are the consolidation step (RB-6, to be filed) that depends on
  both this and [[RB-5]]. Keep this task's edits inside `suts/no_state/**` +
  `tests/test_no_state_clbench.py` so it can run disjoint from RB-5.
- Any container/Dockerfile for the SUT (the keyless offline path needs none).
- `blind_spectrum_monitoring` support — single-task floor is enough for the figure.
