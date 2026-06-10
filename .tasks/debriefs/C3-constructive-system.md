# Debrief: C3 Constructive system end-to-end on the target task under hard reset

**Completed:** 2026-06-07
**Commit:** 657c3d9

## What shipped

`suts/constructive/constructive/clbench_main.py` — a second entrypoint for the
train-and-grow SUT that speaks the **CL-Bench** contract
(`{prompt, response_schema, feedback}` → `{action, resource}`), driven through
the C2 `retention_bench.SubprocessSystem`. It reuses `model`/`train`/`checkpoint`/
`grow` verbatim and:

- takes a bounded gradient step on the *prompt* bytes per query (no separate READ
  stage exists in CL-Bench's single-shot tasks — the query *is* the signal);
- grows capacity on a schedule (default: once, at instance 1; env-tunable cadence
  + layer cap for later experiments);
- flushes the checkpoint to the survive-dir **before** replying, so it survives
  the hard RESET's SIGKILL;
- synthesises a **schema-valid** `action` from the query's `response_schema` via a
  generic JSON-Schema→value walker (object/array/number/integer/boolean/string +
  `$ref`/`$defs`), with leaf values drawn from the model's gibberish generation.

`tests/test_constructive_clbench.py` — 6 tests (skip cleanly without `torch` or
`cl-benchmark`) driving the SUT through the real runner on
`blind_spectrum_monitoring` (variant `five_ch_wide`) under hard-reset schedules,
plus direct-drive assertions on the `compute` UsageEvents. README updated with a
"two entrypoints" section + new env vars.

### Acceptance criteria

- ✅ Constructive SUT runs through `SubprocessSystem` on the C1 target task.
- ✅ Persistent state (checkpoint) lives in the survive-dir and survives hard
  resets; the wiped (stateless) arm measurably differs — proven via
  `train_steps`/`read_count` carrying across SIGKILLs in the stateful arm vs
  restarting when wiped (reward can't show it; see below).
- ✅ Compute `UsageEvent`s populated — per-respond FLOPs (load-bearing), storage
  deltas ~0 in-place with a jump at the growth event.
- ✅ A run completes and emits a `TaskResult`. Gain vs the stateless baseline is a
  **documented negative result** (see Design decisions) — agreed with Toby up
  front.

## Descoped / deferred

- **Reset-axis curve reporting** — C4, explicitly out of scope.
- **Concept-drift / multi-stage schedule path** — used a single *variant*
  (`five_ch_wide`, 13 latent channels incl. 8 dormant = retention signal), not
  the 3-stage `default` schedule. The schedule declares `corpus_id:
  mixed_grid_lifecycle`, so it *requires a frozen corpus on disk* (the task raises
  `FileNotFoundError` otherwise). Generating/locating that corpus is a real
  prerequisite for the C1 concept-drift-on-reset-boundary story → carried to C4
  (see Observations).
- **Multi-step tasks** (poker etc.) — gated on C8; the generic synthesiser will
  be reused there.

## Design decisions

- **New entrypoint, not a bridge inside `SubprocessSystem` (confirmed with
  Toby).** The existing `__main__` speaks the book-track READ/QUIZ contract and
  emits gibberish text; it cannot produce a structured `ScanReport`. Rather than
  pollute the generic C2 adapter with book-track translation + per-task parsing,
  all CL-Bench bridging lives in the SUT (`clbench_main.py`). `SubprocessSystem`
  is unchanged.
- **Generic JSON-Schema→action synthesiser, not a hardcoded `ScanReport`.** A few
  extra lines buy a task-agnostic SUT (works for the next CL-Bench task without a
  rewrite). Unsupported schema nodes (anyOf/enum/const/…) fail loudly rather than
  emitting a silently-invalid action that would crash the runner downstream.
- **Reward gain deliberately NOT asserted.** Gibberish output → meaningless
  report → stateful and wiped arms don't separate on *reward* (observed: 0.18 vs
  0.16, pure noise — stateful was even higher by chance). The retention proof is
  on the survive-dir contents (accumulated training carried vs restarted) + the
  grown checkpoint's loadability after reset, which is what the tests assert.
- **Growth cadence kept at "once at instance 1"** (mirrors B13), with
  `CONSTRUCTIVE_GROW_EVERY` / `CONSTRUCTIVE_MAX_LAYERS` env knobs added so C4 can
  drive richer construction-vs-reset schedules without code change.
- **Action values are model-derived, not constant.** Leaf values stream from the
  model's generation, so the (junk) report genuinely reflects the constructed
  weights and differs between stateful/wiped runs — honest "gibberish from the
  SUT", not a hardcoded empty list.

## Observations

- **`torch` was missing everywhere on the box** — neither the cl-bench 3.13 venv
  nor any other interpreter had it, so the B13 integration test was silently
  *skipping* (`importorskip("torch")`). Installed CPU torch (`2.12.0+cpu`) into
  `/home/agent/src/cl-bench/.venv` via `uv pip install ... --index-url
  .../whl/cpu`. **This is environment state outside the repo** — a fresh dev
  container needs that install to run the constructive tests. `retention_bench`
  itself correctly does *not* depend on torch (it's the generic adapter); torch
  belongs to the constructive SUT's own `pyproject`. Full suite now 100 passed /
  1 skipped (was 87/3 — the 3 torch skips now run).
- **Proof-of-survival is structural, not just an assertion.** A fresh post-reset
  process *must* load the grown checkpoint (else `load_state_dict` mismatches the
  default-shape model and the run crashes). So a clean run through 3 spawns with
  `growth_count == 1` and `n_layers == base+1` is itself evidence the variable-
  size checkpoint round-tripped the SIGKILL.
- **`storage-delta ~0 except at growth` falls out naturally.** Every query
  rewrites the whole `torch.save` blob, so `survive_dir_bytes` is ~constant; the
  only positive delta is the growth instance (the checkpoint gains a block). This
  matches the C3 criterion's "storage-delta ~0 for in-place growth, FLOPs the
  load-bearing cost signal."

## Follow-ups

### Filed
None.

### For C4 to pick up (not separately filed — C4 already exists)
- **Frozen-corpus prerequisite for the drift schedule.** The
  concept-drift-on-reset-boundary story (C1 nuance) needs the `default` 3-stage
  schedule, which requires the `mixed_grid_lifecycle` frozen corpus on disk. C4
  must either generate it (`clbench setup`-style) or stay on seed-driven variants.
  The `ExplicitBoundaries` reset schedule (C2) is the tool for placing resets
  on/off stage boundaries once the corpus is available.

### Considered and dropped
- *File a "verify clean torch install" task.* Done inline (installed + suite
  green). The need is recorded above; no standing task required.
- *A standalone demo/CLI script.* The test **is** the reproducible run (stateful
  vs wiped arms, TaskResult, compute events). A separate script would duplicate
  it; curve reporting is C4.
