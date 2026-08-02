---
status: live
tags: [theory, adus, metrics, cost, messaging]
tasks: []
---

# ADUS mapping

**retention-bench is the instrument for ADUS claims 4 and 9.** The public version
of this note is the "Relationship to ADUS" section in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md); this note carries the reasoning behind
what we did and did not put there.

Source: `/workspace/meta-research/projects/adus-harness/sources/ADUS-tech-report-v1.4.md`.

## Channel taxonomy → SUT classes

ADUS §3.3 classifies memory by **consolidation channel** — the route by which
episode-acquired content reaches a durable form:

| SUT class | Channel | Route |
|---|---|---|
| `no_state` (`P` arm) | **C-N** | none; gains do not outlast the episode |
| notes, retrieval, long-context reload | **C-X** | external artifact, re-presented each session |
| fine-tuning reference | **C-T** | substrate, other-initiated |
| constructive systems | **C-S** | substrate, self-initiated |

The [three-position table](recording-vs-memory.md) is a specialisation of this.
The channel taxonomy is also *why* the SUT interface is mechanism-agnostic: the
reference modes differ in channel, not in kind of claim.

## The two claims

**Claim 9 — reachability (a ceiling).** ADUS §3.2 argues consolidation is an
*ability*, not a rate parameter: without a consolidation route, any competence
needing more acquisition than fits in one episode is unreachable at any effort.
Prediction is a boundary, not slower acquisition. Instrument: `--reset-at` phased
store removal — did capability migrate into the weights, yes/no.

**Claim 4 — slope.** Per-session gain flat-or-decaying under C-X, flat-or-increasing
under C-T/C-S, because the retrieval mechanism does not improve from the gains it
stores. Instrument: the `--reset-every k` uniform sweep.

### We sharpened claim 9 relative to the framework

ADUS states it C-N → C-T. That is nearly trivial here: C-N is only our stateless
floor and beating it is uninteresting. The version worth testing is **C-X → C-S**:
tasks unreachable under an external-artifact channel *at any context budget* that
become reachable under self-initiated substrate update. Flagged in the public
ROADMAP; worth feeding back into ADUS itself.

### Known mismatch: our headline metric measures the wrong one

§3.2's whole argument is that consolidation is reachability-bounded, not
rate-bounded. But normalised retention `(R−P)/(C−P)` swept over `k` is a
**degradation-rate** metric — the reading §3.2 explicitly rejects. The reachability
instrument is the *other* driver (`--reset-at`), currently presented as a
secondary path.

So the two drivers are not two conveniences; they answer different questions
(ceiling vs slope) and the ordering in the docs reflected build order, not weight.

**Resolved 2026-08-02 by routing rather than reordering.** The stronger argument
turned out not to be the framework mapping at all — it was already sitting in
[`phased-store-removal.md`](../../docs/phased-store-removal.md): the *same SUT*
scores `1.000` phased and `0.000` uniform, because resetting mid-learning conflates
"nothing migrated" with "the store wasn't around long enough to learn from". With
the claim now explicitly about consolidation, the uniform sweep was the headline
metric that cannot answer the headline claim.

Swapping which driver is "the headline" was rejected: the keyless reference ladder
— the only committed, calibrated, reproducible numbers — is entirely on the uniform
sweep, and the phased worked example is stale (dated 2026-06-28 on the old
26-instance schedule, needs regeneration at `--reset-at 48`). Leading with a driver
that has no calibration ladder is worse than the mismatch.

So: **retire the concept of a headline; route by claim.** Both drivers are
first-class, each doc says which question each answers, and the calibration gap is
stated rather than hidden. Reorder properly once a phased ladder exists.

## Claim 4 may resolve the cost problem

The ROADMAP's *Exploring* tier is stuck because token counts are not
architecture-neutral (a constructive system spends zero), and any
accuracy-per-cost comparison depends on an assumed query/write ratio — choosing
the ratio chooses the winner.

**A per-session *gain* slope sidesteps all of it.** Dimensionless, needs no cost
accounting, and it is a claim about a curve's shape rather than a level, so it does
not expire when hardware improves. This is the "commit to the slope not the level"
instinct already in the ROADMAP, sharpened from cost-slope to gain-slope. Best
candidate we have; not adopted.

## Convergence worth noting

ADUS §8.2 predicts that if internal simulation requires persistent latent state,
then the internal-simulation objection and the consolidation deficit are *the same
deficit at different timescales*. The Schacter & Addis / Hassabis line
([recording vs memory](recording-vs-memory.md)) says episodic memory and imagining
the future are the same capacity — arrived at from human introspection and lesion
data rather than from architecture. Independent routes to the same link.

## Containment decision

ADUS vocabulary stays **out of the README**. Two reasons, both about credibility:

1. The instrument currently stands on an operational claim anyone can evaluate.
   Binding it to an unpublished framework means a reader who bounces off ADUS
   bounces off retention-bench.
2. It compounds the validity hazard already disclosed. "Co-designed with the system
   expected to do well on it" becomes "co-designed with the system *and* the theory
   that says the system should win" — same author, three artifacts, one loop.

ROADMAP is the right home: it is already the timestamped-before-results document
and already carries the constructive-retention hazard disclosure, so the ADUS
disclosure sits beside a precedent rather than arriving alone.

## Changelog

- 2026-08-02: created alongside the public ROADMAP section.
- 2026-08-02: known-mismatch section resolved — routed by claim rather than
  reordered; recorded why swapping the headline was rejected.
