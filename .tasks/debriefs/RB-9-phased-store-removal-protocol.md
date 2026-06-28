# Debrief: RB-9 Phased store-removal protocol

**Completed:** 2026-06-28
**Commit:** (this commit)

## What shipped

Documented the **phased store-removal** protocol as a first-class use of the
existing `--reset-at` capability, plus empirical verification. No new mechanism:
`ExplicitBoundaries` (RB-8-era) already places a reset at an exact ordinal, so the
phased falsifier is `--reset-at "<train-phase-length>"`.

- `docs/phased-store-removal.md` — the two questions a reset can ask (graceful
  degradation vs migration-into-the-artifact), the conflation uniform resets cause,
  the protocol, the **SUT contract** (store in volatile memory, only the
  consolidated artifact in the survive-dir), a worked example, and a
  when-to-use-which table.
- README pointer + a callout in `docs/metrics.md`.
- `--reset-at` help text now names the phased store-removal use, not just drift
  placement.

## Scope decision (deliberate, kept in-loop)

Did **not** demote retention-bench's uniform reset curve. That uniform "retention
across k resets" curve is the benchmark's headline identity and public artifact;
phased store-removal is presented *alongside* it as the right tool for
migration/understanding questions. The "phased is THE headline" stance is the
episodic project's usage (meta-research D7), not an RB-wide reframe. Surfaced this
distinction rather than silently rewriting RB's framing.

## Verification (the D7 thesis, made visible)

Same learned SUT (`constructive-retention --mode associative-learned`,
`REPLAY_STEPS=60`), same ceiling `C = 0.3077`:

| Protocol | k | R(k) | norm_gain |
|---|---|---|---|
| Phased (`--reset-at 10`) | 1 | 0.3077 | **1.000** |
| Uniform (`--reset-every 1`, CR-6) | 25 | 0.0000 | 0.000 |

Phased `R(1) = C`: the consolidated capability fully survived store removal.
Uniform on the identical model reads as total collapse. The difference is purely
*where the reset lands* — exactly the conflation D7 named. (Ceiling is `8/26`
because 1-hop recall is 8/8 while 2-hop transfer is 0/8; the composition gap is
CR-8's problem, separate from migration.)

`pytest tests/test_gain_curve.py` — 17 pass.

## Follow-ups

- **CR-8** now has both halves unblocked: BYO bijection composition task (via
  RB-8 `--task-spec`) measured with the phased protocol (`--reset-at <train_len>`,
  this task). The remaining research question is the composition gap, not
  migration.
