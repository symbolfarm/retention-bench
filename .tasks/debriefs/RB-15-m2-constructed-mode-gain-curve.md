# Debrief: RB-15 Claim Milestone 2 — constructed-hop2 gain-vs-k curve

**Completed:** 2026-07-29 (executed) / 2026-08-28 (closed out)
**Commit:** run predates this debrief; results recorded in
`constructive-retention/notebook/experiments/RB-15-constructed-hop2-reset-sweep.md`
(committed there as `382e964`, 2026-07-29).

<!-- Closed out retrospectively. The sweep ran on 2026-07-29 and was written up in
     the sibling repo's notebook, but RB-15 was never closed here: TASKS.md still
     read "READY TO RUN ... what remains is the sweep" for five weeks. This debrief
     exists so the two repos stop disagreeing about what happened. -->

## Design decisions

**Where the result lives.** The write-up went into `constructive-retention`'s
research notebook rather than here, because the notebook is that repo's artifact and
the finding is about the constructive SUT's behaviour. That was a reasonable call and
it is why this task drifted: retention-bench owns the *measurement*, so RB-15's
closure belongs here even when the interpretation belongs there. The notebook entry is
authoritative for the numbers; this file is the event record.

**Reset points.** Log-spaced as designed (`--reset-every` 1, 2, 4, 8, 16, 32, 64 →
k = 207, 103, 51, 25, 12, 6, 3). Three seeds throughout; the design allowed escalation
to ~10 at any point showing spread and no point did — spread was exactly zero.

**`CONSTRUCTIVE_HOP2_BASE_CACHE` was set** as the brief required: 28m05s → 3m35s per
arm, bit-identical numbers.

**Raw `R(k)` reported as primary, normalised gain as secondary** — as designed. The
normalised-gain CI is structurally wide ([0.708, 1.346]) because it is a ratio with an
estimated denominator; more seeds will not narrow it.

## Descoped / deferred

**The naive-SGD contrast arm was not run.** This is the significant one. The sweep
design named it explicitly, with the reasoning: *"Without it a flat line is
unfalsifiable — nothing distinguishes 'flat because constructed' from 'flat because
the harness isn't resetting what we think.'"*

What ran instead was a `no_state` control (3 seeds): ceiling 0.3077, `R(k) = 0.000`
at both k=12 and k=207. That **does** discharge the second half of the rationale — a
SUT that holds facts only in RAM scores zero under resets, so the harness demonstrably
resets. It does **not** discharge the first half: nothing in the executed sweep
contrasts constructed-flatness against SGD-degradation on the *same* increment, where
constructive-retention's own baseline reports Δret ≈ −0.98.

The notebook entry's "What it does not show" section does not mention this, so the
gap was invisible from the write-up alone. Picked back up as **RB-24**.

**Milestone 2 is not claimed.** M2 as specified wants `C − P > 0` at non-overlapping
CIs. The structural width of the normalised-gain interval means this run cannot deliver
that, and the notebook says so. RB-15 produced a real first measurement, not the
milestone.

## Observations

**The acquisition threshold is a wrapper property, not an algorithm property.** Below
`every_16` spacing, construction never fires and `R = P` to four decimals. The 16 rule
instances sit contiguously at ~65–80; `every_16` resets at 64 and 80 so the block lands
in one process life, `every_8` splits it at 72, and CR-29 holds the pending rule buffer
in memory only. Even the passing points succeed partly by curriculum alignment — worth
stating in any external write-up, or the flat region reads as more robust than it is.

**`P` is not chance on this task.** `P = 0.3077 = 64/208` — every RECALL correct, zero
TRANSFER. The hop-1 base predates the first prompt under CR-29's base-once design, so
`P` means "base before increment", not "no knowledge". Chance is 1/16. Stated here
because the brief warned it "reads as flattery" otherwise.

**Run logs are gitignored and local**, at `runs/RB-15-2026-07-29/`: `constructed-s{0,1,2}`,
`wide-s{0,1,2}`, `no_state{,2,3}`, and `sweep.sh`. They will not survive a fresh clone.

## Follow-ups

### Filed as tasks

- **RB-24** Naive-SGD contrast arm at extreme k — runs the falsification control the
  RB-15 design specified and the executed sweep omitted.
- **CR-30** Expose the naive-SGD constructor as a `--mode` — RB-24 cannot run without
  it; `NaiveSGDContinue` exists in `baselines.py` but is not reachable through the
  retention-bench wire contract.

### Considered and dropped

- Re-running the whole sweep with more seeds — the spread is exactly zero at every
  point that fires and exactly zero at every point that does not. More seeds measure
  nothing.
- Filing the per-instance-construction follow-up (calibrate against the possible key
  set at startup, removing the acquisition window) as an RB task — it is a
  constructive-retention algorithm change, so it belongs on the CR side. Analysis is
  already written up in `constructive-retention/notebook/notes/acquisition-window.md`;
  left unfiled pending a research-cycle session rather than filed unilaterally.
