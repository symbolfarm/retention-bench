---
title: Worked example — book track, end-to-end event sequence
project: continual-learning-eval
status: structural sketch (placeholder content); produced 2026-05-13 (post-Turn-5)
tags: [worked-example, book-track, structural-sketch]
---

# Worked example — book track, end-to-end

A concrete 10-chapter book run laid out as an atomic event sequence (per [[design-dialogue]] Turn 5 and [[tasks]] Track 1). Chapters are placeholders (`ch_A` … `ch_J`); question sets are abstracted. The point is to show what a full retention curve costs in events, how the probe distribution shapes per-chapter coverage, and where the next layer of friction lives.

This is **not** a first book draft — the actual chapter content and question sets are deferred to the next work-unit (Commit C, pending Toby's asset sign-off). This artifact is the harness-shaped scaffolding the book will fill.

## Run parameters

- Book: 10 chapters, `ch_A` … `ch_J`.
- `RESET`s: 5 (`R1` … `R5`).
- SUT processes: 6 (one per RESET-bounded span: `P0` … `P5`).
- Reads per process: 2 chapters (except the final retention-only process `P5`, which reads 0).
- Probes: `prior` + `ceiling` for every chapter; `retention` at varying `k` per chapter, denser for earlier-read chapters.

The structure is intentionally **staggered**: earlier chapters get longer retention curves, later chapters get shorter ones. This is by construction — a 10-chapter book run can only carry so many retention probes before doubling its event budget. The chapters most worth tracking are the early ones (their retention is the actual research signal).

## Event sequence (39 events, 5 RESETs)

```
─── Process P0 ─────────────────────────────────────
 1.  QUIZ(Q_A,    prior)
 2.  READ(ch_A)
 3.  QUIZ(Q_A,    ceiling)
 4.  QUIZ(Q_B,    prior)
 5.  READ(ch_B)
 6.  QUIZ(Q_B,    ceiling)
 7.  RESET                                     ← R1
─── Process P1 ─────────────────────────────────────
 8.  QUIZ(Q_{A,B}, retention@1)
 9.  QUIZ(Q_C,    prior)
10.  READ(ch_C)
11.  QUIZ(Q_C,    ceiling)
12.  QUIZ(Q_D,    prior)
13.  READ(ch_D)
14.  QUIZ(Q_D,    ceiling)
15.  RESET                                     ← R2
─── Process P2 ─────────────────────────────────────
16.  QUIZ(Q_{A,B}@2, Q_{C,D}@1, mixed-retention)
17.  QUIZ(Q_E,    prior)
18.  READ(ch_E)
19.  QUIZ(Q_E,    ceiling)
20.  QUIZ(Q_F,    prior)
21.  READ(ch_F)
22.  QUIZ(Q_F,    ceiling)
23.  RESET                                     ← R3
─── Process P3 ─────────────────────────────────────
24.  QUIZ(Q_{A,B}@3, Q_{C,D}@2, Q_{E,F}@1, mixed-retention)
25.  QUIZ(Q_G,    prior)
26.  READ(ch_G)
27.  QUIZ(Q_G,    ceiling)
28.  QUIZ(Q_H,    prior)
29.  READ(ch_H)
30.  QUIZ(Q_H,    ceiling)
31.  RESET                                     ← R4
─── Process P4 ─────────────────────────────────────
32.  QUIZ(Q_{A,B}@4, Q_{C,D}@3, Q_{E,F}@2, Q_{G,H}@1, mixed-retention)
33.  QUIZ(Q_{I,J}, prior)
34.  READ(ch_I)
35.  READ(ch_J)
36.  QUIZ(Q_{I,J}, ceiling)
37.  RESET                                     ← R5
─── Process P5 ─────────────────────────────────────
38.  QUIZ(Q_synthesis@final, retention)
        — final-run retention probe combining:
          Q_{A,B}@5, Q_{C,D}@4, Q_{E,F}@3, Q_{G,H}@2, Q_{I,J}@1
          + Q_multi-hop (cross-chapter)
          + Q_thematic   (whole-book)
          + Q_retroactive (early facts cued by late chapters)
39.  (terminate)
```

## Per-chapter retention coverage

| Chapter | Read at | `k` values probed         |
|---------|---------|---------------------------|
| `ch_A`  | step 2  | 1, 2, 3, 4, 5             |
| `ch_B`  | step 5  | 1, 2, 3, 4, 5             |
| `ch_C`  | step 10 | 1, 2, 3, 4                |
| `ch_D`  | step 13 | 1, 2, 3, 4                |
| `ch_E`  | step 18 | 1, 2, 3                   |
| `ch_F`  | step 21 | 1, 2, 3                   |
| `ch_G`  | step 26 | 1, 2                      |
| `ch_H`  | step 29 | 1, 2                      |
| `ch_I`  | step 34 | 1                         |
| `ch_J`  | step 35 | 1                         |

Plus, for each chapter, one `prior` and one `ceiling` probe.

## Cost accounting

- 39 events per seed.
- 10 `READ`s.
- 5 `RESET`s.
- 24 scored `QUIZ`s (10 prior + 10 ceiling + 4 mixed-retention + 1 final synthesis); the mixed and synthesis quizzes aggregate many per-chapter retention probes inside one event.
- At 3 seeds (per [[metrics]] variance default): ~120 events / SUT / asset.

For comparison, the v0.1 design implied roughly 5 stages × 1 quiz × 3 seeds = 15 stages/SUT — but those stages were doing reading-comprehension, not cross-reset retention. The Turn-5 design costs ~3× more events per seed and produces a quantitatively richer signal.

## What this surfaces (frictions to confirm or design around)

The point of writing this out is to find the next layer of decisions. Eight items, ranked by how load-bearing they are:

1. **Mixed-retention `QUIZ` aggregation.** Steps 8, 16, 24, 32 each carry questions probing different chapters at different `k`. The harness needs to deliver these as one `STAGE_INPUT` and recover per-`(q, k)` scores from the `STAGE_OUTPUT`. Two clean options: (a) the `STAGE_INPUT` is a numbered question list and the harness scores each answer independently, looking up its `(chapter, k)` from a side table; (b) the `STAGE_INPUT` is partitioned by tag. Option (a) is simpler and SUT-invisible; recommended.

2. **`prior` probes are issued from a SUT process that has already seen earlier chapters.** Step 4 (`Q_B prior`) lives in process `P0`, which has already read `ch_A`. If `Q_B` contains questions whose answers leak into `ch_A`'s text, the prior baseline is contaminated by within-process state. **Recommendation:** `prior` probes go in the *first* process and *before* any `READ`, batched. Re-plan: move all 10 `prior` probes to a pre-roll at the start of `P0`. Costs an extra event per chapter but cleans up the baseline. Updated sequence below.

3. **`ceiling` probes are within-process by definition.** No friction. The notes-LLM has the chapter still in context; the constructive transformer has the just-grown weights. Both are correct.

4. **Multi-hop and thematic questions need their own probe lifecycle.** A multi-hop question over `ch_A` + `ch_F` only makes sense once both are read. Its `prior` probe (pre-roll) measures "could you answer this from pretraining alone." Its `ceiling` probe must be in the process that read the *later* of the two chapters, after the read. Its `retention` probes are in later processes. The pre-roll handles `prior`; the ceiling slot needs explicit placement. Probably cleanest: add a per-process post-read ceiling slot for multi-hop questions whose later chapter just landed.

5. **Retroactively-relevant questions are a multi-hop subcase.** Question is "about" an early chapter but cued by a later one. Same lifecycle as multi-hop. No special structure needed.

6. **Pre-roll prior probes leak information.** If the SUT sees `Q_F`'s text at step 1 (in a pre-roll), it knows what to listen for when `ch_F` is read later — which is exactly the *adaptive* memory behaviour we want to measure (a notes-LLM that writes "watch for X" beats one that doesn't). **This is correct on reflection.** The retention probe across `RESET` is what enforces memory; pre-reading the questions is just the SUT being clever, and that cleverness is what we're scoring.

7. **`P` is measured once, but the SUT process answering `prior` at step 1 is naive (no chapters read); the SUT answering `retention` at step 38 has read everything.** Their starting states differ. This is fine: `P` is the "what does this SUT know cold" baseline; `R(k)` is "what does this SUT recall after `k` resets." Different SUT states are part of what's being measured.

8. **Final synthesis at step 38.** This is the most valuable scored event but also the most expensive — many questions, all at high `k`. Weighted highest in aggregation. Consider also issuing a `ceiling` for synthesis: at the end of process `P4` (post all reads, pre-`R5`), ask the same synthesis questions. That gives `C_synth` vs. `R_synth` for the headline thematic measurement.

## Revised sequence with the friction-2 fix and friction-8 addition

After moving all `prior` probes to a pre-roll and adding a synthesis ceiling:

```
─── Process P0 (pre-roll + first reads) ──────────────────────
 1.  QUIZ(Q_{A..J,multi,thematic,retro}, prior)   ← single pre-roll
 2.  READ(ch_A)
 3.  QUIZ(Q_A, ceiling)
 4.  READ(ch_B)
 5.  QUIZ(Q_B, ceiling)
 6.  RESET                                          ← R1
─── Process P1 ───────────────────────────────────────────────
 7.  QUIZ(Q_{A,B}, retention@1)
 8.  READ(ch_C)
 9.  QUIZ(Q_C, ceiling)
10.  READ(ch_D)
11.  QUIZ(Q_D, ceiling)
12.  RESET                                          ← R2
─── Process P2 ───────────────────────────────────────────────
13.  QUIZ(mixed-retention @ R2)
14.  READ(ch_E)
15.  QUIZ(Q_E, ceiling)
16.  READ(ch_F)
17.  QUIZ(Q_F, ceiling)
18.  RESET                                          ← R3
─── Process P3 ───────────────────────────────────────────────
19.  QUIZ(mixed-retention @ R3)
20.  READ(ch_G)
21.  QUIZ(Q_G, ceiling)
22.  READ(ch_H)
23.  QUIZ(Q_H, ceiling)
24.  RESET                                          ← R4
─── Process P4 ───────────────────────────────────────────────
25.  QUIZ(mixed-retention @ R4)
26.  READ(ch_I)
27.  READ(ch_J)
28.  QUIZ(Q_{I,J}, ceiling)
29.  QUIZ(Q_synthesis, ceiling)                     ← synthesis ceiling
30.  RESET                                          ← R5
─── Process P5 (final retention) ─────────────────────────────
31.  QUIZ(Q_synthesis, retention@final)
32.  (terminate)
```

32 events. Cleaner, fewer events, all `prior` probes pre-roll, synthesis has both `C` and `R` measured. This is the sketch to take forward into [[interface]] rewriting and book drafting.

## Open follow-ups (not blockers)

- **Pre-roll size.** A single `prior` `QUIZ` with all ~50–100 questions across 10 chapters is large. May want to split into two pre-roll `QUIZ` events for readability / for SUTs whose `STAGE_OUTPUT` size is bounded. Mechanical decision; defer to first-book drafting.
- **Question generation strategy.** Each chapter needs ~5–10 questions across the taxonomy categories. Multi-hop / thematic / retroactive questions are cross-cutting. Memory-targets spec (paired with the book) is the right artifact for this.
- **Action budget per event.** Currently undefined per event-type. `READ` budgets should be generous (reading is the expensive part for constructive SUTs); `QUIZ` budgets tighter. Defer.
- **Variance across event orderings.** Does swapping `READ` order within a process matter? Probably yes for thematic questions. Worth a sensitivity check once we have a real book.
