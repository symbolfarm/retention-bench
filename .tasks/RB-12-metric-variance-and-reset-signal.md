# RB-12 Metric variance story + post-reset-window reward (un-dilute the reset signal)

**Priority:** medium-high
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `retention_bench/gain_curve.py`, `scorer/aggregate.py` (or its folded home from
RB-11), `docs/metrics.md`

## Context

Review 2026-07-07 conceptual concerns 1 & 3. Two things keep the headline `R(k)` curve from
being publishable:

1. **`R(k)` is a whole-run mean, which dilutes the reset signal it exists to measure.** A run
   with one reset at instance 30 of 90 scores 30 pre-reset instances identically to the
   ceiling arm, so the reset's damage is averaged against instances it couldn't affect. Two
   consequences: curve sensitivity depends on run length + reset placement, and — worse — a
   SUT that *relearns quickly* after a reset is indistinguishable from one that *retained*.
   Separating those is arguably the benchmark's actual question.
2. **No variance story.** Every arm is a single run; `docs/metrics.md` §Reporting already
   requires error bars + seed counts, but nothing computes them. With binary rewards over ~26
   instances the reward resolution (~0.038) is comparable to ε=0.05 itself, so a one-run point
   on a possibly-narrow normalised band can be noise.

## Goal

A retention curve that (a) reports uncertainty and (b) has a companion metric separating
retention from relearning, so the curve is trustworthy enough to publish.

## Acceptance criteria

- [ ] **Post-reset-window reward:** mean reward over the first `m` instances after each reset
      (the reward-side analogue of the already-specified cold-start *compute* metric),
      reported alongside whole-run `R(k)`. This is what distinguishes "retained" from
      "relearned fast."
- [ ] **Bootstrap CIs** over per-instance `outcomes` (already retained per point "for post-hoc
      reanalysis") on each curve point; rendered as error bars.
- [ ] **ε scales with `r_max`:** an absolute 0.05 is ~8% of achievable range on tasks whose
      whole-run mean is structurally compressed by unscored train instances
      (`r_max = 16/26 ≈ 0.615`); make ε relative to `r_max` (document the choice).
- [ ] `docs/metrics.md` updated: define the post-reset-window reward, the bootstrap procedure,
      and a footnote that `k` indexes count-not-placement (two arms with equal `k` and
      different placement are different experiments — the `--reset-at` drift story).

## Decisions already made

- **Complementary, not replacement:** keep whole-run `R(k)` (it reconciles with CL-Bench's
  `mean_gain` by construction/test — don't break that); add the post-reset-window reward
  beside it. (Review 2026-07-07 concern 1.)

## Out of scope

- Re-deriving or replacing the band formula / the CL-Bench reconciliation.
- A full shape-classifier / AURC implementation (those stay specified-not-implemented; see
  RB-14's metric-status marking).
