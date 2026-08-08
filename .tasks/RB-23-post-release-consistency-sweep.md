# RB-23 Post-release consistency sweep after the first LLM measurement

**Priority:** medium
**Blocked by:** RB-19 (first agentic LLM measurement)
**Touches:** `README.md`, `docs/ROADMAP.md`, `docs/reference-ladder.md`, `RELEASING.md`

## Context

Several public documents encode "as of v0.1.0, no language model has been measured". That is
true now and will be false the moment RB-19 lands. Before v0.1.0 those statements drifted
privately; now they drift in a released tag that the CL-Bench authors and anyone else have been
pointed at.

The statements are spread across files and will not all be noticed by whoever lands RB-19:

- `README.md` §Scope and limits — "No language model has been measured yet… the central claim is
  therefore unfalsified in either direction".
- `docs/ROADMAP.md` §Status — the same claim, plus "five keyless synthetic reference systems and
  one constructive system".
- `docs/ROADMAP.md` §Confidence tiers → Likely — "Language-model and retrieval systems measured
  through the instrument" moves out of *Likely* once it has happened.
- `docs/reference-ladder.md` — "the keyless ladder is what CI runs" stays true, but the framing
  around it assumes keyless is all there is.

## Shape

One pass, after RB-19 produces a number, that moves all of these together and decides how
model-dependent results are presented alongside the deterministic ladder.

## Checklist

- [ ] Update the four locations above so no released document claims no LLM has been measured.
- [ ] Apply the two-tier publication rule already committed to in the ROADMAP: reproducible
      keyless numbers in one place; model-dependent numbers as dated snapshots with pinned model
      IDs and stored traces, kept visibly separate. Decide *where* the second tier lives — a new
      `docs/results/` directory is the obvious candidate and does not exist yet.
- [ ] Decide the version bump. Per `RELEASING.md`, adding results does not change what an
      existing number means, so this is a minor bump unless the metric moved.
- [ ] Re-run the clean-checkout gate before tagging (the ladder must still reproduce exactly).

## Acceptance

- No public document states that no language model has been measured.
- Model-dependent results are visibly separated from the deterministic ladder, dated, and pinned
  to a model ID.
- The clean-checkout ladder reproduction still passes.

## Notes

Do not fold this into RB-19 itself. RB-19 is a measurement task and should not be gated on a
documentation decision about publication structure; equally, the docs should not be updated
piecemeal by whoever happens to notice one of the four locations.
