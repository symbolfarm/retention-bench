# RB-21 Phased store-removal reference ladder

**Priority:** medium
**Blocked by:** none
**Touches:** `suts/` (2–3 new keyless SUTs), `docs/phased-store-removal.md`,
`docs/reference-ladder.md`, `run.sh` (a `ladder-phased` target), CI

## Context

As of the 2026-08-02 doc pass, retention-bench routes by claim rather than
promoting one headline metric: the uniform `--reset-every k` sweep answers graceful
degradation, phased store removal (`--reset-at`) answers whether capability
migrated into the durable artifact. The instrument's central claim is a
consolidation claim, so phased store removal is the protocol that bears on it most
directly.

**But only the uniform sweep has a calibration ladder.** Phased store removal has
exactly one worked example: one real SUT (`constructive-retention --mode
associative-learned`), regenerated 2026-08-02 on the default 112-instance schedule,
scoring `norm_gain = 1.000` phased against `0.000` uniform. There is no floor rung,
no chance line, and no partial-consolidation rung run through this protocol, and it
is not in CI.

So the protocol is **argued** to discriminate rather than **demonstrated** to. That
gap is now stated openly in `README.md`, `docs/metrics.md` and
`docs/phased-store-removal.md` — this task closes it. It is also the work that
would let the ordering actually change rather than merely be routed.

See [`notebook/notes/instrument-scaling-limits.md`](../notebook/notes/instrument-scaling-limits.md)
for why this sits *behind* RB-19 in priority despite being cheaper.

## Shape

Mirror the existing uniform ladder: keyless, deterministic, offline, no API key and
no model weights, reproducible from a clean checkout, run by CI.

Rungs should differ precisely in **migration behaviour**, not in retention
generally:

- **persists its raw store to the survive-dir** — after removal should collapse to
  ~`P`. Doubles as the control that catches the SUT-contract violation
  `docs/phased-store-removal.md` warns about (if the store is in the survive-dir,
  the protocol degenerates to store-present).
- **buffers episodes in RAM, checkpoints only a consolidated artifact** — should
  score ~`C`. The "migrated" rung.
- **partial consolidation** — consolidates a fixed fraction, should land strictly
  between. This is the rung that shows the protocol has *resolution*, not just a
  binary.

A chance rung is probably unnecessary — `random_guess` already exists and its
behaviour under `--reset-at` is degenerate — but confirm rather than assume.

## Acceptance

- `./run.sh ladder-phased` (or equivalent) runs offline, keyless, deterministic.
- The three rungs separate in the expected order, with the middle rung strictly
  between floor and ceiling.
- Committed numbers + interpretation in `docs/phased-store-removal.md` (or a
  sibling doc), in the same style as `docs/reference-ladder.md`.
- CI runs it.
- The "no phased ladder exists yet" caveats in `README.md`, `docs/metrics.md` and
  `docs/phased-store-removal.md` are removed or rewritten to point at the result.

## Notes

The existing worked example's `norm_gain` CI is wide (`[0.643, 1.538]`, percentile
bootstrap over 112 per-instance outcomes). Keyless deterministic rungs should not
have that problem, but check whether the band is wide enough at the default
schedule to separate a partial rung cleanly — if not, the schedule may need
lengthening for this ladder specifically.
