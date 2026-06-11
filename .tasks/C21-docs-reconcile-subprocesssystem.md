# C21 Reconcile sut-interface.md + metrics.md to the SubprocessSystem contract

**Priority:** medium
**Blocked by:** nothing
**Touches:** `docs/sut-interface.md`, `docs/metrics.md`, `docs/README.md`

## Context

C20 retired the book-track and made `retention_bench.gain_curve` +
`SubprocessSystem` the only path. But two public docs were authored for the
book-track and only got *minimal* C20 coherence fixes (dangling cross-refs +
reference-SUT lists), not a rewrite — because a full rewrite was out of C20's
scope. Both now carry a C20 note flagging the gap and pointing here.

1. **`docs/sut-interface.md`** still describes the book-track event contract as
   its spine: `READ`/`QUIZ` events over a tagged `STAGE_INPUT`, the structured
   `answers` list, the `agentic | in-context` *leaderboard* split, and a
   `sut-manifest.json` whose canonical example is the (deleted) `no_state`
   SUT's `entrypoint`. The **live** SUT contract is `SubprocessSystem`'s
   one-line-JSON query/reply per CL-Bench instance, launched via
   `clbench_entrypoint`. The launch/container/`DIR`/`RESET` mechanics in the doc
   are still accurate and authoritative — it's the *event vocabulary* and the
   manifest/entrypoint shape that are stale.
2. **`docs/metrics.md`** opens with ~90 lines of the per-question `P`/`C`/`R(k)`
   probe formulation (book-track) before the reset-axis gain-curve section. The
   per-question framing should become *background/definition* for the band
   metric, with the whole-run reset-axis curve as the primary, live formulation.

This is a public-credibility artifact (CL-eval doubles as the outward-facing
piece — see `[[project_cleval_dual_purpose]]`), so the SUT-building doc reading
as a contract that no longer exists is a real reviewer-facing problem.

## Goal

`sut-interface.md` describes the `SubprocessSystem` contract a SUT actually
implements today (query/reply JSON, `clbench_entrypoint`, the `kind:"local"`
resource self-report), and `metrics.md` leads with the reset-axis gain curve;
no doc presents the retired book-track as live. Remove the C20 "tracked
separately" notes once done.

## Acceptance criteria

- [ ] `sut-interface.md` rewritten to the `SubprocessSystem` wire contract:
      the per-instance JSON query/reply shape (replace the `READ`/`QUIZ` /
      `STAGE_INPUT` / `answers` framing), the `clbench_entrypoint` manifest field
      and a kept-SUT example (not `no_state`), and the survive-dir/`RESET`
      mechanics retained. Decide the fate of the `agentic | in-context`
      leaderboard split (CL-Bench's own leaderboard may subsume it).
- [ ] `metrics.md` restructured so the reset-axis gain curve is the primary
      formulation and the per-question `P`/`C`/`R(k)` text is background for the
      band-metric definition; nothing reads as a live book-track pipeline.
- [ ] The C20 "tracked separately / see the C20 debrief" notes are removed from
      both docs once the rewrite lands.
- [ ] `docs/README.md` index blurbs still match the rewritten docs.
- [ ] `scripts/promote.sh dryrun` clean.

## Relevant files

- `docs/sut-interface.md`, `docs/metrics.md`, `docs/README.md`
- `retention_bench/system.py` (the live `SubprocessSystem` contract), the kept
  SUTs' `clbench_main.py` + `sut-manifest.json` (`notes_llm`, `constructive`,
  `bsm_accumulator`) as the source of truth for the wire shape + manifest fields.

## Out of scope

- Any code change — this is docs-only.
- The orphan-`main` cutover (C17), though C17 should run after this so the
  public docs are coherent in the first snapshot.
