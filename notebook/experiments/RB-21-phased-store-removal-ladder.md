---
status: live
tags: [reset, consolidation, calibration, validity, keyless]
tasks: [RB-21]
command: "./run.sh ladder-phased"
verdict: mixed
---

# RB-21 Phased store-removal calibration ladder

## Hypothesis

The phased store-removal protocol (`--reset-at`, a single reset at the
train/probe boundary) discriminates *migration into the durable artifact* from
its absence, and does so with resolution — a system that consolidated part of
what it learned should land strictly between the floor and the ceiling.

## Setup

Keyless, offline, deterministic; `symbolic_associative_retention` on its default
112-instance schedule (48 train, 64 probes, boundary at ordinal 48). Seven rungs,
each run on **both** arms in one table: phased (`boundaries:48`) and uniform
(`every_1`). The variable rungs are one SUT,
[`suts/consolidating_memory`](../../suts/consolidating_memory/), which buffers
episodes in RAM and writes a derived artifact to the survive-dir in batches of 8,
under three settings of `CONSOLIDATION_FRACTION`. Committed numbers and the full
reading are in
[`docs/phased-store-removal.md`](../../docs/phased-store-removal.md).

## Results

| rung | phased `norm_gain` | uniform `norm_gain` |
|---|---:|---:|
| `no-state-floor` | 0.000 | 0.000 |
| `consolidate-none` (f = 0.0) | 0.000 | 0.000 |
| `consolidate-partial` (f = 0.5, ordinal) | 0.500 `[0.348, 0.679]` | 0.000 |
| `consolidate-partial-hashed` (f = 0.5, hashed) | 0.344 `[0.209, 0.508]` | 0.000 |
| `consolidate-full` (f = 1.0) | 1.000 `[0.792, 1.245]` | 0.000 |
| `raw-store-control` (`associative_memory`) | 1.000 `[0.792, 1.245]` | 1.000 |

`P = 0.0000`, `C = 0.5714` for every rung above; the `random-guess-chance` rung's
band is EXCLUDED (`P == C == 0.0268`) on both arms, confirming the brief's guess
that a chance rung is degenerate under this protocol rather than informative.

## Verdict

**Mixed, and the failure is the useful half.**

Supported: the protocol has resolution. The partial rung lands strictly between
floor and ceiling rather than snapping to an end, so partial consolidation is
visible as partial. The floor/ceiling separation is complete and keyless.

Not supported as stated: **the phased number alone does not identify
consolidation.** The last two rows are numerically identical and mean opposite
things. `raw-store-control` persists its raw store to the survive-dir, so the
hard reset never removes it, the protocol degenerates to the store-present
condition, and it scores a perfect migration verdict for the wrong reason. The
SUT contract in `docs/phased-store-removal.md` already named this hazard; what is
new is that it is now *measured*, and that it is invisible to the protocol it
compromises.

The uniform arm is what separates them: a batch consolidator scores 0.000 there
(its buffer never reaches the batch size before the next kill) while the
store-present SUT scores 1.000 on both. **So the reportable unit is the pair, not
the phased number.** That also reproduces the worked example's `1.000` phased /
`0.000` uniform contrast on keyless machinery, which was previously only
available from a real learned SUT.

## What the partial number is not

The two partial rungs run the same fraction and score differently. The task gives
object `i` attribute `i % A`; the ordinal selector migrates every other episode
and therefore migrates exactly the objects whose attribute rules also migrated,
so 2-hop transfer survives at the same rate as 1-hop recall and `norm_gain`
lands on the migration fraction exactly. Migrate independently per fact
(`hashed`) and transfer survives at roughly the square of the recall rate: 0.344.

A partial score is therefore a joint fact about the SUT's migration behaviour
**and** the task's structure. Read it as a position between floor and ceiling,
not as a fraction of capability. The exactness of the 0.500 was the most
seductive number in this run, and it is the one that means least.

## Limits

- One task, one schedule. Nothing here shows the ladder holds at other widths.
- Resolution stops at thirds: fraction 0.25 (`0.250 [0.136, 0.390]`) and 0.5
  (`0.500 [0.348, 0.679]`) have overlapping intervals at `n = 112`. Finer
  resolution needs a longer schedule, not a different metric.
- The rungs are hand-built to exhibit the mechanism they are named for. A ladder
  is a validity demonstration, not evidence about any real system.
