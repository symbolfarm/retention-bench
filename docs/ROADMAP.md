# Research agenda

**Last revised 2026-08-08, ahead of the v0.1 release.** This is a research agenda, not a
benchmark specification. It records what we think we are measuring and what we intend to
measure next, written before the measurements exist so that the design is on record ahead of
the results. What fixes that record is the git history of this file, not the prose: from v0.1
onward, every revision is a public commit with a date on it.

Nothing here is a commitment to a finding. Where we state an expectation, we state it as a
question we intend to answer.

---

## What this instrument is for

Retention Bench adopts [Continual Learning Bench](https://arxiv.org/abs/2606.05661)'s (Asawa
et al., Apache-2.0) runner, task interface and evaluation contract, and points them at a
different question, using a **hard RESET** — a process-kill discontinuity where only an on-disk
survive-dir persists — and a **mechanism-agnostic SUT contract**, under which fine-tuning,
structural growth, notes and retrieval are all modes above one process-level interface.

It is a research instrument that we use and share, not a benchmark seeking submissions. There
is no leaderboard and no submission process. "Bench" here means *workbench*.

### The claim it exists to test

> Continual learning agents need expanding memory: episodic memory growing across sessions;
> semantic memory growing across episodes.

Two levels, and they are not the same requirement. The first asks that experience survive a
discontinuity that erases working state. The second asks that it be abstracted — that the
system end up knowing things no single episode contains. The first is cheap: write to disk.
The second is what this instrument measures.

The distinction that does the work is between a **recording** and a **memory**. A recording is
verbatim, retrieved unchanged, and complete: it answers any question whose answer sits inside a
single stored item, and nothing else. A memory has been **re-represented** — stored in a form
other than the one it arrived in, and one that supports queries the arrival form does not.

Two things re-representation is not. It is not the same as **lossiness**: lossiness is a
frequent symptom, not the definition, and random deletion is lossy while structuring nothing.
And it is not the same as **compression**: lossless compression removes redundancy while
producing nothing queryable, and a growing semantic index re-represents without shrinking at
all. Capacity pressure is one reliable *cause* — you cannot answer about `N` items from less
than `N` items' worth of storage without exploiting regularity, and exploiting regularity is
structure — which is why the storage-budget axis below is a way to force the issue. It is a
cause, not the definition. The claim under test is explicitly about memory that **expands**, so
the instrument must not accidentally require that memory shrink.

This is **not** a claim that transformers cannot abstract. Within a context window they plainly
do: attention composes over the whole window, and a model shown instances of a rule can induce
it and apply it to an input it never saw. That is abstraction *within an episode*, and it is
what transformers are best at. The claim is about where that abstraction goes: it is computed
at query time and discarded with the process, and what persists is the token sequence that
produced it.

| | what persists | where it abstracts | consequence |
|---|---|---|---|
| **In-context learning** | nothing | query time, richly | the abstraction dies with the process |
| **Retrieval / notes** | a recording | query time, over a retrieved subset | re-derived every session, from a subset |
| **Consolidation** | the abstraction | write time | kept |

The middle row's limitation is structural rather than incidental: retrieval selects by query,
so a system cannot abstract over what it did not retrieve, and questions whose answers are
properties of the entire set have no query that surfaces them. This is the specific reason we
expect the aggregation rung below to be hard for retrieval, and it does not require denying
in-context learning any of its compositional power.

**How this could be wrong.** A well-built agentic harness that manages context and retrieval
aggressively may show no limit we can discern at the scales we can test. That is the live
possibility, and open questions 1–3 are where we confront it.

**How it could be shown false.** A system that clears the probe ladder with nothing but a
store. That result is ambiguous on its own, and the two readings are distinguishable by what
the probe asks for: a store passing a probe whose answer sits inside a single stored item means
the rung was too easy; a store passing probes whose answers are properties of the whole set is
evidence against the claim.

### Why a hard RESET

The obvious objection is that longer context windows will make this moot. They will not. A
long-context system can always reload everything from disk when the process restarts — a
legitimate strategy that works, and costs the full re-read **every session, forever.** Without
resets that cost is paid once and amortised across a run, so the difference between
paying-per-session and paying-once is invisible. **The hard RESET converts a one-time cost into
a recurring one**, which is what makes the difference measurable. The reset is not a handicap
applied to retrieval systems; it is the mechanism that exposes a scaling difference that is
otherwise hidden.

---

## The organising axis

We think there is one axis underneath, not a collection of independent difficulty knobs:
**how far the probe sits from the episode that taught it** — how much of the answer had to
become semantic memory rather than remain episodic.

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

### What would count as success

The top rung is the target, not a stretch goal: a system that acquires genuinely new competence
during a run — including competence that *corrects* something it previously held — and applies
it to inputs it has never seen, in domains where the answer can be checked independently. An
instrument that measured only whether a system can restate what it was told would be measuring
the bottom rung and calling it the whole thing. The tiers below describe what is *scheduled*;
this is what the schedule is aimed at, and the two are deliberately different.

### Read the profile, not the level

A corollary: **a perfect score on Recall is not by itself good news** — verbatim fidelity is
what a recording is *for*. The informative quantity is the *shape* across rungs, not the height
at any one:

| Profile | Reading |
|---|---|
| high recall, cliff immediately above | a recording |
| moderate recall, graded decline with distance | a memory |
| flat at chance | nothing retained |

We do not predict that reconstruction is *required* — that would be an argument from human
architecture, and this instrument is substrate-neutral. The functional version is what we
claim: a store that keeps only the arrival form, under no pressure to re-represent, has no
route to the upper rungs. If a system clears every rung on a verbatim log, that refutes the
claim and we would report it as such.

### Two invariants

**Acquisition happens during the run.** The operation being tested must be learned from the
episode stream, not brought in from pretraining. Reasoning benchmarks hand you the rule and
test whether you can apply it; this instrument hands you no rule and tests whether you can
acquire one. That is why the current curriculum uses nonce symbols.

**Probes use held-out inputs.** At every rung, the test input must be one the system never saw
in that role. Without this, a lookup table over taught pairs passes while representing
nothing.

### The elicitation ceiling

Nonce symbols make acquisition airtight but cap what the instrument can say about real
competence. Any move to real material runs into the same problem: **behavioural absence is not
representational absence.** A model that cannot do X may still hold all the substructure, so a
measured gain confounds *acquisition* with *elicitation of latent competence*. We have measured
exactly this confound in the sibling project: in constructive-retention's CR-21, the base model
recalls a held-out attribute at 1.0 while the key derived to reach it fails to transfer — the
information is present, but not reachable by the probe.

So real material is admissible **provided the elicitation ceiling is measured as a control
arm**: the base model given maximal in-context help (few-shot, hints, staged elicitation), with
consolidation counted only where it beats what elicitation alone recovers. This applies to every
candidate below; it is not specific to any one of them.

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
- **Storage budget as an axis.** If storage is free, a recording is never punished. Probes a
  recording structurally cannot answer are one way to separate recording from memory; a
  capacity constraint is the second, independent one, because capacity pressure forces a system
  to choose between keeping records and keeping conclusions. Reported under a stated budget
  rather than as a general claim.

### Exploring

- **What the realistic acquisition target is.** Nonce symbols are contamination-proof but
  synthetic. Two candidates are more real, and neither is settled:

  *Post-cutoff codebases* — material created after a model's training cutoff, verified by the
  repo's own test suite. Contamination-proof by date, cheap, and interpretable. The catch is
  shelf life: every model generation moves the cutoff, so the corpus needs refreshing and a
  result is not directly re-runnable on a newer model. Idiom is also not novel even when the
  code is, so the elicitation control arm above does real work here.

  *Knowledge gaps in small models* — abundant and stable, with no expiry. The catch is that the
  confound is at its sharpest: a gap in behaviour is exactly where latent-but-unreachable
  competence is most likely, so the control arm moves from prudent to mandatory.

  Both are admissible and they are not the same experiment; we have committed to neither.
  *Invented formalism* — a formal system, curriculum and verifier built from scratch — is
  contamination-proof by construction but expensive and hard for a reader to interpret. We do
  not expect to reach for it, and it stays available if it turns out to be cheap or necessary.

- **How to measure cost.** Cost matters, but capability gates and cost compares: among systems
  that clear the capability bar cost is the whole comparison, and where nothing separates on
  capability there is nothing to price. We have no defensible metric yet. Token count is not
  architecture-neutral — a constructive system spends *zero*, which makes it vacuous exactly
  where it matters most — and any accuracy-per-cost ratio depends on an assumed query/write
  mix, where choosing the mix chooses the winner.

  One candidate is to report **how cost grows with accumulated history** rather than its level:
  a growth rate is dimensionless and therefore comparable across architectures, where an
  absolute cost is not. We are not sold on it. The more likely outcome is that there is no
  single architecture-neutral number: different memory mechanisms may simply win on different
  measures, qualitatively as well as quantitatively, and the honest report is a profile rather
  than a ranking.

- **Procedures that change.** A learned procedure that is revised mid-stream — the convention
  updated, the interface changed, the policy rewritten — is ordinary in real work and, we
  suspect, badly handled by retrieval. We are not aware of anyone measuring it.

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

This instrument is developed alongside `constructive-retention`, a research project on
gradient-free constructive learning, by the same author. That project builds systems this
instrument is intended to measure, and we expect them to do well on it. It is not public yet,
so there is nothing to link to; **nothing constructive ships in this repository**, and its
systems reach this harness through the documented process-level SUT contract.

That is a genuine validity hazard and we would rather name it than have it noticed. Two things
we do about it: the probe design and the thesis are published here before those systems are
measured through the instrument, so the design is timestamped ahead of the favourable result;
and the instrument is built so that a third party can point it at their own system through a
documented process-level contract rather than having to take our word for anything.

We would rather be told the instrument is measuring the wrong thing now than after we have
published results on it.

## Relationship to ADUS

The same author is developing a functional architecture of intelligence called **ADUS**. It is
not yet gathered into a single published form, so there is nothing to cite. Nothing here
depends on accepting it — the claim, the probes and the metric are all stated without it — but
it is where several of the design decisions above came from, and it is our own framework, which
is a reason to disclose the connection rather than to lean on it.

ADUS classifies memory by **consolidation channel**, the route by which content acquired in an
episode reaches a durable form, and those channels map onto the reference SUT classes directly:
`no_state` → C-N (no route), notes/retrieval/long-context reload → C-X (external artifact),
fine-tuning → C-T (substrate, externally initiated), constructive systems → C-S (substrate,
self-initiated). That taxonomy is what the three-position table above specialises, and it is
why the instrument treats these as modes above one contract: they differ in channel, not in
kind of claim. Two ADUS claims are directly at stake — a **reachability** boundary under C-X
(measured by phased store removal, [`phased-store-removal.md`](phased-store-removal.md)) and a
per-session **gain slope** (measured by the uniform reset sweep). The full mapping, including
where our metric does not yet match the claim it is meant to test, is in
[`../notebook/notes/adus-mapping.md`](../notebook/notes/adus-mapping.md).

---

## Status

As of this document, the instrument has measured five keyless synthetic reference systems —
four retention mechanisms plus a chance line — and one constructive (weights-mutating) system
through a real process-kill reset. That constructive measurement was of an out-of-tree system
reached through the process contract; it is **not reproducible from this repository**, and the
reference ladder a reader can run covers the keyless systems only.

It has measured **no language model**. The central claim is therefore unfalsified in either
direction. Coherence is not evidence, and the first real measurement is the immediate next
step.

**Neither driver is the headline.** The uniform `k`-sweep and phased store removal answer
different questions and are routed by the claim being made: ceiling for consolidation, slope
for degradation. The keyless reference ladder is calibrated on the uniform sweep only; building
a phased ladder is the work that would let that ordering change.
