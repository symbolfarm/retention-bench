# retention-bench — research notebook

> Entry point for the project's current understanding. Notes are living documents
> (updated in place); `log/` is the append-only session narrative. See the
> `research-notebook` skill for conventions.
>
> **Bootstrap note (2026-08-02):** seeded by the pre-v0.1 messaging/philosophy
> session. Most durable material still lives in [`docs/`](../docs/) — this INDEX
> maps over it, and existing docs migrate into `notes/` incrementally when a task
> touches their territory.
>
> `notebook/` is **not** in [`PUBLIC_PATHS`](../PUBLIC_PATHS) — it is dev-only and
> never reaches the public `main` snapshot. Framework-internal reasoning (ADUS,
> validity-hazard deliberation) belongs here rather than in `docs/`.

## The claim

> Continual learning agents need expanding memory: episodic memory growing across
> sessions; semantic memory growing across episodes.

Two levels, and not the same requirement. The first asks that experience survive a
discontinuity that erases working state — cheap, write to disk. The second asks
that it be abstracted, and is what the instrument measures. Falsifiable by a
system that clears the probe ladder with nothing but a store.

Public statements: [`README.md`](../README.md) §"The claim it exists to test",
[`docs/ROADMAP.md`](../docs/ROADMAP.md).

## Current best understanding

- [Recording vs memory](notes/recording-vs-memory.md) — the distinction the claim
  rests on; the three positions (ICL / retrieval / consolidation); the
  episodic×persistence 2×2 and why the axes collapse for LLMs; the reconstruction
  literature. **Ground floor; read first.** Contains the ICL correction —
  "in-context learning produces access without integration" was **false** and is
  retired.
- [The episodic→semantic axis](notes/episodic-semantic-axis.md) — what the probe
  ladder measures, and the **profile-across-rungs** reading: a perfect Recall score
  is what a *recording* looks like, so read the shape, not the height.
- [ADUS mapping](notes/adus-mapping.md) — channel taxonomy → SUT classes; ADUS
  claims 4 (slope) and 9 (reachability) as what the instrument is for; the known
  mismatch between our headline metric and the reachability reading; why ADUS stays
  out of the README.

Not yet migrated — still authoritative in `docs/`:
[`metrics.md`](../docs/metrics.md) (scoring),
[`sut-interface.md`](../docs/sut-interface.md) (the process contract),
[`reference-ladder.md`](../docs/reference-ladder.md) (committed keyless numbers),
[`phased-store-removal.md`](../docs/phased-store-removal.md) (the `--reset-at`
ceiling driver).

## Open questions

Full list in [`docs/ROADMAP.md`](../docs/ROADMAP.md) §"Open questions". Live at the
notebook level:

1. **Does the profile-across-rungs prediction hold?** Recording = high recall +
   cliff; memory = graded decline. Untested; needs a rung above composition.
2. **Ceiling or slope as the headline metric?** `--reset-at` answers the
   reachability question ADUS §3.2 says is the real one; the `k`-sweep is
   currently the headline. Deferred past v0.1 — see
   [ADUS mapping](notes/adus-mapping.md).
3. **Real vs invented mathematics** for the long-horizon rung, and whether an
   elicitation-ceiling control arm is enough to admit real mathematics. See
   [2026-08-02](log/2026-08-02.md).
4. **No language model has been measured yet.** The central claim is unfalsified
   in either direction.

## Log

- [2026-08-02](log/2026-08-02.md) — pre-v0.1 messaging and philosophy pass:
  new claim, ICL correction, recording-vs-memory taxonomy, storage budget promoted,
  ADUS section added.
