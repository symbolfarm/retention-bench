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

> Continual learning agents need expanding memory: episodic memory growing across sessions;
> semantic memory growing across episodes.

Two levels, and they are not the same requirement. The first asks that experience survive a
discontinuity that erases working state. The second asks that it be abstracted — that the
system end up knowing things no single episode contains. The first is cheap: write to disk.
The second is what this instrument measures.

The distinction that does the work is between a **recording** and a **memory**. A recording is
verbatim, retrieved unchanged, and complete: it answers any question whose answer sits inside a
single stored item, and nothing else. A memory has been compressed into a structure — which is
why it composes, and why it is lossy. Compression is not a defect here; it is what forces
structure, and a store under no pressure to compress never acquires any.

This is **not** a claim that transformers cannot abstract. Within a context window they plainly
do: attention composes over the whole window, and a model shown instances of a rule can induce
it and apply it to an input it never saw. That is abstraction over episodes, and it is what
transformers are best at. The claim is about where that abstraction *goes*. It is computed at
query time and discarded with the process; what persists is the token sequence that produced
it.

Three positions, then, rather than two:

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

The claim can be shown false, and the falsification is cheap to state: a system that clears the
probe ladder with nothing but a store.

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

### What would count as success

The top rung is the target, not a stretch goal. An instrument that measured only whether a
system can restate what it was told would be measuring the bottom rung and calling it the whole
thing.

What we want to be able to detect is a system that acquires genuinely new competence during a
run — including competence that *corrects* something it previously held — and applies it to
inputs it has never seen, in domains like mathematics and programming where the answer can be
checked independently.

We are a long way from that. As of this document the instrument has measured five keyless
synthetic reference systems and one constructive system, and no language model at all. The
tiers below describe what is *scheduled*. This describes what the schedule is aimed at, and the
two are deliberately different.

---

## The organising axis

We think there is one axis underneath, not a collection of independent difficulty knobs:
**how far the probe sits from the episode that taught it** — how much of the answer had to
become semantic memory rather than remain episodic.

Distance from surface form is the observable proxy. The underlying quantity is the
episodic→semantic transition: recall asks only that the episode survived, and each rung above
it asks for something no single episode contains.

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

### Read the profile, not the level

A corollary of the recording/memory distinction: **a perfect score on Recall is not by itself
good news.** Verbatim fidelity is what a recording is *for*. Human episodic memory is
notoriously inaccurate, and the inaccuracy is not incidental — it is the signature of having
been compressed into a structure, which is the same compression the upper rungs depend on.

So the informative quantity is the *shape* across rungs, not the height at any one:

| Profile | Reading |
|---|---|
| high recall, cliff immediately above | a recording |
| moderate recall, graded decline with distance | a memory |
| flat at chance | nothing retained |

We do not predict that reconstruction is *required* — that would be an argument from human
architecture, and this instrument is substrate-neutral. The functional version is what we
actually claim: compression is what forces structure, and a store under no pressure to compress
never acquires any. If a system clears every rung on a verbatim log, that refutes the claim and
we would report it as such.

This also generalises the scoring note under *Likely* below. Distance-based rather than
exact-match scoring is not special pleading for aggregation; it follows from what a memory is.

### Two invariants

**Acquisition happens during the run.** The operation being tested must be learned from the
episode stream, not brought in from pretraining. Reasoning benchmarks hand you the rule and
test whether you can apply it; this instrument hands you no rule and tests whether you can
acquire one. That is why the curriculum uses nonce symbols.

For the long-horizon mathematics direction, the invariant admits two routes. *Invented*
mathematics is contamination-proof by construction, but expensive: it needs a formal system, a
curriculum, and a verifier built from scratch, and the result is hard for a reader to interpret.
*Real* mathematics past a small model's measured knowledge frontier is far cheaper on all three
— but **behavioural absence is not representational absence.** A model that cannot do X may
still hold all the substructure: notation, manipulation rules, the shape of the argument. A gain
then confounds *acquisition* with *elicitation of latent competence*. We have measured exactly
this confound in the sibling project: in constructive-retention's CR-21, the base model recalls
a held-out attribute at 1.0 while the key derived to reach it fails to transfer — the
information is present, but not reachable by the probe.

So real mathematics is admissible **provided the elicitation ceiling is measured as a control
arm**: the base model given maximal in-context help (few-shot, hints, staged elicitation), with
consolidation counted only where it beats what elicitation alone recovers. Absent that control,
invented formalism remains the default.

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

- **Storage budget as an axis.** Promoted from *Exploring* on a structural argument rather than
  an application one. We had justified it by deployment setting — disk is effectively free on
  servers, genuinely scarce on edge devices — which made it look like a niche constraint. The
  stronger reason: **if storage is free, a recording is never punished**, and the
  recording/memory distinction becomes unmeasurable by that route entirely. We currently have
  exactly one way to separate them — probes a recording structurally cannot answer — and a
  capacity constraint is the second, independent one. Capacity pressure is what forces a system
  to choose between keeping records and keeping conclusions. The axis will still be reported
  under a stated budget rather than as a general claim, and it grows in importance as corpus
  size grows: at pre-training scale, keeping the recording stops being free even on a server.

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

## Relationship to ADUS

The same author maintains a functional architecture of intelligence called **ADUS**
(github.com/symbolfarm/intelligence). It is not a prerequisite for anything above, and nothing
in this instrument depends on accepting it — the claim, the probes, and the metric are all
stated without it. This section records the mapping because the framework is where several of
the design decisions above came from, and because two of its registered claims are the
questions this instrument exists to answer. It is our own framework, which is a reason to
disclose the connection rather than to lean on it.

ADUS classifies memory by **consolidation channel** — the route by which content acquired in an
episode reaches a durable form. The channels map onto the reference SUT classes directly:

| SUT class | ADUS channel | Route |
|---|---|---|
| `no_state` (the `P` arm) | **C-N** | none; gains do not outlast the episode |
| notes, retrieval, long-context reload | **C-X** | external artifact, re-presented each session |
| fine-tuning reference | **C-T** | substrate, initiated by something other than the agent |
| constructive systems | **C-S** | substrate, self-initiated |

That taxonomy is what the three-position table above is a specialisation of, and it is why the
instrument treats fine-tuning, structural growth, notes, and retrieval as modes above one
process-level contract: they differ in channel, not in kind of claim.

Two ADUS claims are directly at stake.

**Reachability (ADUS claim 9).** ADUS argues consolidation is an *ability* rather than a rate
parameter, on the grounds that without a consolidation route any competence needing more
acquisition than fits in one episode is unreachable at any effort. The prediction is a
reachability boundary, not slower acquisition: there exist tasks unreachable under C-X *at any
context budget* that become reachable under C-S. Note this is sharper than the version in the
framework, which compares against C-N — C-N is only our stateless floor, and beating it is not
interesting. The instrument for this claim is the **phased store removal** driver
(`--reset-at`, see [`phased-store-removal.md`](phased-store-removal.md)), which asks whether
capability migrated into the weights: a ceiling question with a yes/no answer.

**Slope (ADUS claim 4).** Under matched task streams, per-session gain is predicted to be flat
or decaying under C-X and flat or increasing under C-T/C-S, because the retrieval mechanism
does not itself improve from the gains it stores — nothing makes the next gain easier. The
instrument for this claim is the **uniform reset sweep** (`--reset-every k`), which measures
degradation as resets accumulate.

Two consequences worth stating plainly.

*The two drivers answer different questions, and neither is the headline.* The `k`-sweep was
presented as primary, which reflected the order the two were built rather than their weight —
and left the instrument leading with a metric that cannot cleanly answer its own central claim.
Both are now first-class, routed by the claim being made: ceiling for consolidation, slope for
degradation. This is a documentation change, not a metric change; the keyless reference ladder
is still calibrated on the uniform sweep only, and building a phased ladder is the work that
would let the ordering actually change.

*Claim 4 may resolve the cost problem in the Exploring tier above.* The obstacle there is that
token counts are not architecture-neutral, which makes any accuracy-per-cost comparison
depend on an assumed query/write ratio. A per-session *gain* slope sidesteps this entirely: it
is dimensionless, it needs no cost accounting, and it is a claim about the shape of a curve
rather than a level, so it does not expire when hardware improves. We have not adopted it as
the cost metric, but it is the most promising candidate we have.

---

## Status

As of this document, the instrument has measured five keyless synthetic reference systems —
four retention mechanisms plus a chance line — and one constructive (weights-mutating) system
through a real process-kill reset. It has measured **no language model**. The central claim is
therefore unfalsified in either direction. Coherence is not evidence, and the first real
measurement is the immediate next step.
