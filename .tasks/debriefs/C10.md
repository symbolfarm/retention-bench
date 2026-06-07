# Debrief: C10 Frozen corpus for the concept-drift reset schedule

**Completed:** 2026-06-07
**Commit:** 5b5437e

## What shipped

The `default` three-stage `blind_spectrum_monitoring` schedule now runs
end-to-end through `SubprocessSystem`, and the gain-curve driver can place hard
resets *on* vs *off* a concept-drift boundary.

- **`retention_bench/bsm_corpus.py`** — reproducible (re)generator/verifier for
  the `mixed_grid_lifecycle` frozen corpus. Wraps CL-Bench's own
  `build_rollout_corpus` + `write_scan_corpus`. `verify_corpus()` regenerates
  into a temp dir and compares sha256 (mutates nothing); `ensure_corpus()`
  (re)writes into the cl-bench data dir if missing. CLI:
  `python -m retention_bench.bsm_corpus [--verify|--force]`.
- **`retention_bench/gain_curve.py`** — new `--reset-at "O1,O2,..."` CLI flag
  (repeatable) → one `ExplicitBoundaries` arm each, alongside `--reset-every`.
  This is the surface for deliberate on/off-drift placement.
- **`retention_bench/_clbench.py`** — re-exported `build_rollout_corpus`,
  `write_scan_corpus`, `default_corpus_paths` (the single `src.*` chokepoint).
- **Tests:** `tests/test_bsm_corpus.py` (3 — byte-exact regeneration vs committed
  sha256, on-disk == regen, default schedule constructs without FileNotFoundError
  with drift boundaries at 30/60/90); `tests/test_gain_curve.py` +3
  (ExplicitBoundaries measured-k, placement→k, `--reset-at` CLI parsing).
- **Docs:** `docs/metrics.md` gained a *Placing resets on a concept-drift
  boundary* subsection (drift semantics + `--reset-at` + corpus prerequisite);
  constructive SUT README gained a drift-sweep pointer.

**Acceptance criteria — all met:**
1. `default` 3-stage schedule runs through `SubprocessSystem` without
   `FileNotFoundError` (corpus present; `test_default_schedule_constructs...`).
2. An `ExplicitBoundaries` sweep placing resets on `{30,60}` vs just-after
   `{35,65}` ran via `retention_bench.gain_curve` and produced a curve (full
   90-instance, 4-arm run; rendered output below).
3. Corpus generation documented + reproducible (`bsm_corpus` regenerates the
   committed bytes exactly; `--verify` proves it; tests pin it).

### The delivered curve (on-drift vs just-after, constructive SUT)

```
Reset-axis retention curve  (system: constructive-drift)
  prior   P  (stateless baseline) = 0.1964
  ceiling C  (no-reset, k=0)      = 0.1460
  band    C - P                   = -0.0504   [EXCLUDED: < epsilon, curve undefined]

    k  schedule             R(k)  norm_gain  clbench_gain    n
  ---  ----------------  -------  ---------  ------------  ---
    2  boundaries:30,60   0.1460      —           -0.0504   90
    2  boundaries:35,65   0.1460      —           -0.0504   90
```

The band is negative/excluded — expected and in-scope: the constructive SUT
emits gibberish (C3), so reward carries no retention signal and placement can't
yet move the curve. C10 delivers the corpus + placement *machinery*; the
non-monotonic shape awaits a retaining-but-imperfect SUT (out of scope, per the
brief). The artifact lives at `runs/c10-drift-sweep/curve.txt` (gitignored).

## Descoped / deferred

- **SUT reward quality** — explicitly out of scope; the gibberish SUT keeps the
  band excluded, so the on/off-drift arms render identically. Documented as the
  honest current state, not hidden.
- **AURC / summary statistics over the curve** — out of scope (also deferred by
  C4).
- **`run.sh` wrapper for the drift sweep** — the CLI is the runnable driver;
  `run.sh` is still book-track-shaped (same call C4 made). Not C10 scope.

## Design decisions

- **Corpus is *located*, not generated-from-scratch.** Discovery: the
  `mixed_grid_lifecycle` corpus already ships **git-tracked inside the
  cl-benchmark dependency** (`data/blind_spectrum_monitoring/`), so the
  FileNotFoundError the brief anticipated does not occur on a fresh clone. I
  pivoted the deliverable from "create the missing file" to "document where it
  lives + a deterministic regenerator + a test pinning byte-identity." Stronger
  reproducibility story (provenance is checkable) without mutating the
  dependency repo. The regenerator's default target *is* the cl-bench data dir so
  it can still fill a genuinely-missing corpus.
- **Off-drift arm = just-after `{35,65}`** (not just-before). Surfaced to Toby
  with the drift mechanics; chosen because it most cleanly isolates the *timing*
  effect — on-drift discards the now-stale prior (potential benefit), just-after
  discards fresh correct adaptation (pure cost), k matched at 2. Just-before
  conflates "wiped still-valid belief" with the drift-clearing benefit. The
  placement is a CLI arg, trivially changed.
- **BSM corpus symbols routed through `_clbench.py`.** They're task-specific
  rather than core-interface, but the "never import `src.*` outside the
  chokepoint" discipline (C4) is worth more than the purity of keeping the
  chokepoint interface-only.
- **`EXPECTED_SHA256` hardcoded** in `bsm_corpus.py` as a regression pin. If a
  future CL-Bench bump changes the DGP/seeds, `test_regenerates_committed_bytes`
  fails loudly rather than silently shifting the corpus under the experiment.

## Observations

- The driver needed **zero changes** to run the multi-stage schedule — the BSM
  task manages stage transitions internally (90 instances across 3 stages), and
  `run_reset_sweep` already accepts arbitrary `ResetSchedule`s. Confirmed C4's
  "data prerequisite, not a code gap" call; the only code was the `--reset-at`
  CLI ergonomics + the corpus wrapper.
- **Drift boundaries = corpus stage `end_scan_idx` = `{30, 60}`** (1-based
  completed-instance ordinals). Read straight off
  `task._frozen_corpus_metadata.stages`.
- The first **background** launch of the sweep produced empty output with no live
  process (cause undiagnosed — possibly a detach/flush issue with the inline-env
  compound command). Re-running foreground with `-u` worked fine. Worth noting
  for future long SUT sweeps: prefer foreground `-u` + `tee`, or verify the bg
  job actually spawned before walking away.
- Sweep wall-clock: ~minutes, dominated by the **prior arm** (wipe-every-instance
  = 90 torch subprocess spawns). Ceiling/drift arms are 1 and 3 spawns.

## Follow-ups

### Considered and dropped

- *File a "retaining-but-imperfect SUT for a shaped drift curve" task.* The need
  is real (it's what makes the non-monotonic story visible) but it's squarely
  SUT-reward-quality work, already the known gap from C3 and named in C6's
  conditional. No new standing task — it surfaces naturally when a non-gibberish
  SUT is built.
- *`run.sh reset-curve` wrapper.* Same call as C4; a separate cleanup if/when the
  pivot path graduates out of the book-track `run.sh`. Not worth a task yet.
