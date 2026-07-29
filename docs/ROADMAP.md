# Research agenda

**Dated 2026-07-29.** This is a research agenda, not a benchmark specification. It records
what we think we are measuring and what we intend to measure next, published *before* the
measurements exist so that the design is on record ahead of the results.

Nothing here is a commitment to a finding. Where we state an expectation, we state it as a
question we intend to answer.

---

## What this instrument is for

Retention Bench is an extension to [Continual Learning Bench](https://arxiv.org/abs/2606.05661)
(Asawa et al., Apache-2.0) contributing two things it does not have: a **hard RESET** — a
process-kill discontinuity where only an on-disk survive-dir persists — and a
**constructive/parametric system class**.

It is a research instrument that we use and share, not a benchmark seeking submissions. There
is no leaderboard and no submission process. "Bench" here means *workbench*.

### The claim it exists to test

> **Storage is not memory.** A system can have complete access to every token it has ever seen
> and still not know anything.

The operational difference is composition. A fact that has been *integrated* combines with
other facts you never anticipated combining it with, without anything prompting you to go
look. A fact that has been *stored* requires first recognising that you need it, then
retrieving it, then reasoning over the retrieved text.

So the claim under test is not "language models forget." It is sharper: **in-context learning
produces access without integration.** Everything in the window is available for lookup, but
it does not restructure the system, so it does not compose the way learned knowledge composes.
Retrieval is in-context learning with a bigger drawer — it improves access and does nothing
for integration.

### Why a hard RESET

The obvious objection is that longer context windows will make this moot. They will not,
because of what the reset does.

A long-context system can always reload everything from disk when the process restarts. That
is a legitimate strategy and it works. And it costs the full re-read **every session, forever.**

Without resets, that cost is paid once and amortised across a run, and the difference between
paying-per-session and paying-once is invisible. **The hard RESET converts a one-time cost
into a recurring one**, which is what makes the difference measurable. The reset is not a
handicap applied to retrieval systems; it is the mechanism that exposes a scaling difference
that is otherwise hidden.

---

## The organising axis

We think there is one axis underneath, not a collection of independent difficulty knobs:
**how far the probe sits from the surface form of what was taught.**

| Probe family | What it asks | What it tests |
|---|---|---|
| **Recall** | the probe restates the taught form | episode retention |
| **Composition** | the answer requires joining two taught items; deepens with hop count | concept formation |
| **Aggregation / absence** | the answer is a property of the whole set, never taught as an item | abstraction over experience |
| **Revision** | the answer requires knowing which of two taught items is current | updating what is believed |
| **Application** | apply a procedure that was learned during the run, to an input never seen | skill |

Every rung is a case of *the answer is not contained in any single stored item*. Retrieval
works exactly when the distance is zero, and we expect it to degrade as the distance grows —
though how fast, and whether iterative retrieval changes the shape, is precisely what we do
not yet know.

Only **Recall** and a two-hop **Composition** probe exist today.

### Two invariants

**Acquisition happens during the run.** The operation being tested must be learned from the
episode stream, not brought in from pretraining. Reasoning benchmarks hand you the rule and
test whether you can apply it; this instrument hands you no rule and tests whether you can
acquire one. That is why the curriculum uses nonce symbols, and it is why the long-horizon
direction below requires *invented* mathematics rather than real mathematics — real
mathematics measures pretraining.

**Probes use held-out inputs.** At every rung, the test input must be one the system never saw
in that role. Without this, a lookup table over taught pairs passes while representing
nothing.

---

## Confidence tiers

### Committed

- Hard process-kill RESET with an on-disk survive-dir, as the discontinuity all measurements
  are taken across.
- The keyless reference ladder stays deterministic, offline, and reproducible from a clean
  checkout. It is the calibration layer, and it is what CI runs.
- Probe design and thesis published before the systems we build are measured against them.
- Held-out inputs and in-run acquisition, as above.

### Likely

- **Revision probes.** A fact or rule is re-taught with a new value mid-stream, and the probe
  asks for the current one. We expect this to be hard for retrieval for a structural reason:
  the store contains both versions, correctly, with no basis for choosing between them. Unlike
  plain multi-hop, iterating does not obviously help — it compounds the ambiguity at each hop.
- **Aggregation and absence probes**, scored by distance rather than exact match. A system
  that reconstructs "about forty" from episodic traces when the answer is forty-two has done
  something real, and exact-match scoring would record it as complete failure.
- **Language-model and retrieval systems measured through the instrument**, including an
  agentic system capable of more than one retrieval before answering. Naive single-shot
  retrieval is a calibration rung, not a result.
- **Two-tier publication.** Reproducible keyless numbers in one place; model-dependent numbers
  as dated snapshots with pinned model IDs and stored traces, kept visibly separate.

### Exploring

- **How to measure cost.** We believe cost matters as much as accuracy — retrieval pays at
  query time and integration pays at write time — but we do not yet have a defensible metric.
  Token count is not architecture-neutral: a constructive system spends *zero* tokens, which
  makes the metric vacuous exactly where it matters most. Any accuracy-per-cost comparison
  also depends on an assumed ratio of queries to writes, and choosing that ratio chooses the
  winner. Token counts are gameable by terser notation, and query-time tokens conflate memory
  access with reasoning.

  Our current best idea is to **commit to the slope rather than the level**: absolute cost is
  not comparable across architectures, but *how cost grows with accumulated history* is
  dimensionless and therefore is. That is a claim about the shape of a curve rather than about
  what any system can do today, so it does not expire when hardware improves. We are not
  confident enough in it to commit.

- **Storage budget as an axis.** On servers, disk is effectively free and capping it is an
  artificial constraint. On edge and embedded devices — arguably the more interesting setting
  for continual learning — it is a real one, and capacity pressure is exactly what forces a
  system to choose between keeping records and keeping conclusions. Valid under a stated
  deployment regime, not as a general claim.

- **Procedures that change.** A learned procedure that is revised mid-stream — the convention
  updated, the interface changed, the policy rewritten — is ordinary in real work and, we
  suspect, badly handled by retrieval. We are not aware of anyone measuring it.

- **Learning mathematics or programming from scratch.** The far end of the ladder: a small
  model acquiring genuinely novel formal operations during a run and applying them to unseen
  inputs. Skills sit on this ladder rather than outside it — applying a learned procedure is
  what understanding is *for*, and stopping at recall would be measuring the bottom rung and
  calling it the whole thing. Long-horizon and not scheduled.

---

## Open questions

These are the questions the next round of measurement is meant to answer. We do not know the
answers, and we have deliberately not predicted them.

1. Does **iterative** retrieval close the composition gap? A system that retrieves twice —
   the attribute, then the rule keyed on it — should be able to solve two-hop composition that
   single-shot retrieval structurally cannot. Does it, in practice, and does it keep working
   as hops deepen?
2. Does iterative retrieval close the **revision** gap, or does iterating compound the
   ambiguity?
3. How large is the **anticipation gap** — the difference between aggregate questions the
   system was told to expect and questions revealed only at test time? A system told in advance
   what to count can simply count. The interesting measurement is what remains answerable from
   a compression chosen before the question was known.
4. Does query-time cost **scale with accumulated history** for retrieval-based systems and stay
   flat for integrated ones, as the framing above predicts?
5. Does a system that is additive **by construction** retain across a real process-kill reset,
   and is retention flat in the number of resets?

---

## Relationship to constructive-retention

This instrument is developed alongside [constructive-retention](https://github.com/symbolfarm/constructive-retention),
a research project on gradient-free constructive learning, by the same author. That project
builds systems this instrument is intended to measure, and we expect them to do well on it.

That is a genuine validity hazard and we would rather name it than have it noticed. Two things
we do about it: the probe design and the thesis are published here before those systems are
measured through the instrument, so the design is timestamped ahead of the favourable result;
and the instrument is built so that a third party can point it at their own system through a
documented process-level contract rather than having to take our word for anything.

We would rather be told the instrument is measuring the wrong thing now than after we have
published results on it.

---

## Status

As of this document, the instrument has measured five keyless synthetic reference systems —
four retention mechanisms plus a chance line — and one constructive (weights-mutating) system
through a real process-kill reset. It has measured **no language model**. The central claim is
therefore unfalsified in either direction. Coherence is not evidence, and the first real
measurement is the immediate next step.
