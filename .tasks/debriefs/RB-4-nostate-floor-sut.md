# Debrief: RB-4 No-state (ephemeral) reference SUT — the retention floor

**Completed:** 2026-06-24
**Commit:** e5a1db2

## What shipped

A keyless, offline `no_state` reference SUT under `suts/no_state/`, mirroring the
`associative_memory` structure: `no_state/__init__.py` + `no_state/clbench_main.py`,
`pyproject.toml`, `sut-manifest.json`, `README.md`, plus
`tests/test_no_state_clbench.py`.

It answers the same `symbolic_associative_retention` TRAIN/RECALL/TRANSFER
protocol as `associative_memory`, but keeps memory only in-process (an in-RAM
dict for the process lifetime). It has no `_load_state`/`_save_state` and never
reads or writes `RETENTION_BENCH_DIR`. So recall holds within an episode (k=0)
and collapses to the prior floor for k>=1, because each hard RESET kills the
process and erases the un-persisted state.

### Floor curve numbers (gain_curve, keyless/offline)

Command (exactly the acceptance-criteria command):

```
.venv/bin/python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m no_state.clbench_main" \
  --extra-pythonpath suts/no_state \
  --reset-every 1 --reset-every 2 --name no-state-floor
```

```
  prior   P  (stateless baseline) = 0.0000
  ceiling C  (no-reset, k=0)      = 0.6154   (= 16/26)
  band    C - P                   = 0.6154

    k  schedule        R(k)     norm_gain  clbench_gain   n
   12  every_2         0.0000   0.000      0.0000         26
   25  every_1         0.0000   0.000      0.0000         26
```

C == 16/26 matches the `associative_memory` ceiling (same task, same band).
Every stateful hard-reset arm sits at the floor `R(k) = P = 0`, normalised gain
0 — the floor is demonstrated.

## Descoped / deferred

Followed the task's "Out of scope" list exactly: no reference-ladder figure, no
README/`run.sh` reference-SUT-list edits (that is RB-6), no container/Dockerfile,
no `blind_spectrum_monitoring` support. All edits stayed inside
`suts/no_state/**` + `tests/test_no_state_clbench.py`.

## Design decisions

- **Ephemeral (in-RAM) rather than truly stateless** — pre-decided in the task
  brief; documented in the SUT README and the floor curve confirms the intended
  drop from R(0)=0.6154 to R(k)=0 rather than a flat line.
- **`model_id` / manifest `name` = `no-state`** (hyphen), package = `no_state`
  (underscore), matching the `associative_memory` convention (manifest name
  `associative-memory`, package `associative_memory`).
- **Resource accounting kept identical in shape** to `associative_memory`
  (flops/tokens estimate) for ladder comparability; only `model_id` differs.

## Observations

- The gain_curve driver owns survive-dir isolation, so the floor behaviour comes
  entirely from the SUT never persisting — no harness cooperation needed.
- The test asserts the *inverse* of the `associative_memory` test: ceiling above
  prior (within-episode learning is real) AND every reset arm collapses to the
  prior (`mean_reward`/`clbench_mean_gain`/`normalised_gain` all ≈ 0). This pins
  both ends of the contract.
- `promote.sh dryrun` only lists tracked files; the new files appeared after the
  work commit. Leak check is clean either way.

## Follow-ups

### Considered and dropped

- A shared helper module to dedupe the prompt-parsing logic now duplicated
  between `associative_memory` and `no_state`. Dropped: each SUT is intentionally
  self-contained (own `pyproject.toml`, launched via `--extra-pythonpath`), and
  the divergence (persistence vs none) is the whole point — coupling them via a
  shared module would undercut that and complicate the reference-ladder story.
