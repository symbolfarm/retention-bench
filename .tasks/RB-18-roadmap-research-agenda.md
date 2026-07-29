# RB-18 Write the roadmap as a research agenda (pre-registration)

**Priority:** high
**Blocked by:** nothing
**Touches:** `docs/ROADMAP.md` (new), `README.md` (link only — coordinate with RB-17)

## Context

From the 2026-07-29 pre-release discussion. This document exists for a specific reason, and
the reason determines how it should be written.

**Purpose: pre-registration.** retention-bench is co-designed with constructive-retention, the
system expected to do well on it, and CR's constructed hop-2 is already at ceiling. That is a
real validity hazard and a reader will spot it. Publishing the probe design and the thesis
*before* CR is measured through the instrument timestamps the design ahead of the favourable
result. That is the difference between "a benchmark my method happens to win" and "here is
what I said I would measure, then measured."

This argues for publishing **soon and loosely**. Precision is not what does the work; the
timestamp is.

**Pre-register the questions, not the conclusions.** The tempting version says "we will show
that LLMs and RAG fail to compose after a hard reset." If iterative retrieval turns out to
handle composition well — plausible — that is a public commitment to walk back. State what
will be measured instead: does iterative retrieval close the composition gap? the revision
gap? how large is the gap between disclosed and undisclosed aggregation queries? Same content,
reads as science rather than advocacy, and it is more credible precisely because the question
was named before the answer was known.

**The organising axis** (settled 2026-07-29): a single ladder of *distance from the stored
surface form*, which also maps onto Toby's ADUS framework (Abilities/Dispositions/
Understanding/Skills):

| Probe family | What it asks | ADUS |
|---|---|---|
| Recall | probe restates the taught form | episode retention |
| Composition | answer requires joining two taught items; deepens with hops | concept formation |
| Aggregation / absence | answer is a property of the whole set, never taught as an item | understanding |
| Revision | answer requires knowing which of two taught items is live | updating understanding |
| Application to novel inputs | apply a procedure learned in-session | skill |

Every rung is a case of *the answer is not in any single stored item*. Retrieval works exactly
when the distance is zero and degrades as it grows.

**The invariant that keeps this coherent:** the operation must be **acquired during the run,
not brought in from pretraining**. Reasoning benchmarks hand you the rule and test application;
this instrument hands you no rule and tests acquisition. That line is also why the long-term
mathematics/programming direction needs *invented* mathematics — real maths measures
pretraining, not acquisition.

**Held-out novel inputs at every rung**, or a lookup table passes wearing a skill costume.

## Goal

A short public `docs/ROADMAP.md` that states the thesis, the ladder, the open questions, and
what is committed versus speculative — written loosely enough that it does not become a
commitment device, and dated so it functions as pre-registration.

## Acceptance criteria

- [ ] `docs/ROADMAP.md` exists, is dated, and is titled as a **research agenda**, not a
      benchmark roadmap.
- [ ] Three explicit confidence tiers: **Committed / Likely / Exploring**. Anything unresolved
      goes in Exploring — in particular the cost metric.
- [ ] The probe ladder is stated as one axis with the ADUS mapping, not as five independent
      difficulty dials.
- [ ] The acquisition-in-session invariant is stated, with the contamination argument for
      invented mathematics as the long-horizon direction.
- [ ] Open questions written as **questions**, not predicted results. At minimum: does agentic
      (iterative) retrieval close the composition gap? does it close the revision gap? how
      large is the anticipation gap between disclosed and undisclosed aggregation probes? does
      query-time cost scale with history for retrieval and stay flat for integration?
- [ ] The cost-metric problem recorded honestly in Exploring, including why token count is not
      architecture-neutral (a constructive SUT spends zero tokens, which makes the metric
      vacuous exactly where it matters) and the current best idea — **commit to the slope, not
      the level**, since growth-with-history is dimensionless and comparable across
      architectures where absolute cost is not.
- [ ] Storage budget recorded as a *conditional* axis, valid under an edge/embedded regime and
      not as a universal scarcity claim.
- [ ] The co-design relationship with constructive-retention stated plainly.
- [ ] Linked from the README (coordinate with RB-17).

## Relevant files

- `docs/ROADMAP.md` — new
- `README.md` — link target (RB-17 owns the surrounding copy)
- `docs/associative-curriculum.md` — the existing task spec the ladder extends
- `TASKS.md` — the CL-Bench pivot decision, for framing consistency

## Decisions already made

- **Publish loosely, not precisely.** The value is the timestamp. Over-specification creates
  sunk-cost pressure on a design that moved three times in one conversation.
- **Questions, not conclusions.** Protects credibility and protects against a walk-back.
- **One axis, not six knobs.** Six-knob designs get reported at one setting and the other five
  rot; a single ordered ladder produces one memorable figure (probe family on x, one line per
  system — retrieval falls off a cliff, integration stays flat).
- **Cost stays in Exploring.** Four unresolved objections: not architecture-neutral; the result
  depends on an assumed query-to-write ratio, which means picking the ratio picks the winner;
  gameable by terser notation; query tokens conflate memory access with reasoning.
- **Skills belong on the ladder.** "It looks like reasoning" is not a reason to stop — under
  ADUS, skill is application of understanding and understanding is integration of episodes, so
  a memory instrument that stops at recall is measuring the bottom rung and calling it the
  whole ladder. The near-term probes stay on the memory side regardless.

## Out of scope

- Implementing any new probe family. This document describes; it does not build.
- Settling the cost metric. It goes in Exploring precisely because it is unsettled.
- Benchmark machinery of any kind — leaderboard, submission process, frozen splits.
