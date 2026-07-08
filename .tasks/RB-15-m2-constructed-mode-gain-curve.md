# RB-15 Claim Milestone 2: wire the constructed SUT into a `--mode` + take the gain-vs-`k` curve

**Priority:** high
**Blocked by:** nothing (same-repo); **BLOCKED externally — do not start until CR-22 lands**
**Depends-on (external):** constructive-retention **CR-22** (constructed hop-2 — the first SUT
increment that is additive *by construction* rather than by SGD replay)
**Touches:** `constructive_retention/` (a `--mode` exposing the constructed-hop-2 model as an
SUT — likely split into a small CR-side companion task when picked up), `retention_bench/gain_curve.py`,
`docs/metrics.md`, `docs/brief.md` (M2)

## Context

This is the **cross-repo keystone** the 2026-07-06 CR reviews *and* the 2026-07-07 RB review
all point at from opposite sides:

- The retention-bench brief's **Milestone 2** — `C − P > 0` at non-overlapping CIs on the
  gain-vs-`k` curve — is still **unclaimed**. It is the thing that makes the project
  externally legible, and none of the harness work feeds a non-degenerate band yet.
- retention-bench currently ships a constructive SUT whose band correctly renders **`EXCLUDED`**
  (collapsed, `C ≈ P`). The gap *is* M2.
- The external CR review predicts the shape a real constructed increment should produce:
  **retention flat in `k`** (constructed knowledge has no buffer to lose), which would be the
  first non-degenerate band the benchmark was built to display.

CR-22 (constructed hop-2) is the first SUT whose increment is additive/online by construction
(`base_weight_delta==0`, `grad_steps==0`, survives RESET) rather than acquired by the SGD
replay the North Star defines itself against. That is the SUT this task measures.

**Why filed now but blocked:** recorded so it isn't lost, but it must not start until CR-22
produces a real constructed increment — otherwise there is nothing non-degenerate to measure.

## Goal

Run the actual phased gain-vs-`k` protocol against the constructed-hop-2 SUT and either claim
M2 (`C − P > 0`, non-overlapping CIs) or record precisely why the band is still degenerate.

## Acceptance criteria

- [ ] A `--mode` (CR-side; likely a small companion task) exposes the constructed-hop-2 model
      through the standard SUT wire contract, driven by the harness like any other SUT.
- [ ] The phased `--reset-at` protocol (RB-8/RB-9) runs against it; the gain-vs-`k` curve is
      produced with the RB-12 variance story (bootstrap CIs) so "non-overlapping CIs" is
      actually testable.
- [ ] M2 verdict recorded: either `C − P > 0` at non-overlapping CIs (claim it in `brief.md` +
      `metrics.md`), or a precise diagnosis of the remaining degeneracy.
- [ ] If it clears: check the predicted **retention-flat-in-`k`** shape and note it as the
      first non-degenerate band.

## Decisions already made

- **Blocked on CR-22, not CR-19** — the constructed *hop-2* is the additive-by-construction
  increment; CR-19's 1-hop additivity demo is a substrate step, not the SUT measured here.
  (2026-07-08.)
- **Uses RB-12's bootstrap CIs** — "non-overlapping CIs" is only meaningful once variance is
  computed, so RB-12 is a soft prerequisite on the measurement side.

## Out of scope

- Building the constructor itself (that's CR-22).
- Any BSM / blind-spectrum-monitoring external-validity task — this claims M2 on the
  bijection curriculum first.
