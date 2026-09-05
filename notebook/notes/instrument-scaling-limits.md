---
status: live
tags: [instrument, metrics, scaling, validity, priorities]
tasks: [RB-19, RB-21]
---

# Where the instrument will strain

**The substrate is right; the strain is in the metric layer.** Assessment made
2026-08-02, zooming out from the pre-v0.1 doc pass to ask whether this workbench is
a suitable starting point for [what would count as success](../INDEX.md#what-would-count-as-success).

That is the good version of the problem: the substrate is expensive to change
later, the metric layer is comparatively cheap.

## What holds

Four things are load-bearing and I would not change them for the ambition:

- **The process-kill reset with an on-disk survive-dir.** A real discontinuity that
  cannot be faked, indifferent to mechanism. Nothing about mathematics or coding
  requires changing it.
- **The mechanism-agnostic subprocess contract.** What lets the instrument be
  pointed at a fine-tuner, a RAG agent, a constructive learner or a frontier model
  without privileging any. This is what makes it an instrument rather than a demo.
- **`--task-spec`.** Mathematics and coding curricula can live outside this repo,
  so the instrument doesn't have to grow a domain in order to measure one.
- **Band exclusion when `C ≈ P`.** Refusing to score beats scoring badly, and it
  generalises.

## Three strains, in expected order of biting

**1. Cost per arm does not survive scale.** Each arm runs the full instance stream;
a sweep is `P` + `C` + one arm per `k`, so ~6 full passes. Free for keyless
synthetic SUTs, ruinous for an LLM over a large corpus — and Toby's stated target
is a pre-training-like regime of many gigabytes. The design silently assumes cheap
SUTs and no doc says so. This may force a different sampling design rather than a
tweak.

**2. The prior `P` stops being a clean floor once an LLM is the SUT.** Band
normalisation assumes `P` is a stable stateless baseline. For a language model on
real mathematics, `P` *is* pretrained competence: prompt-sensitive,
temperature-sensitive, and raisable by elicitation effort. That is the same
elicitation-ceiling problem now written into ROADMAP §"Two invariants" — but here
it lands in the **denominator of the headline metric**. The hardest quantity to
measure becomes the one everything is divided by.

**3. Run-mean scoring dilutes acquisition events.** Everything is scored as a
whole-run mean reward, but the ambition is about a *transition* — couldn't do it,
then could. A mean washes that out, and the sparser the event the worse it gets.
**This has already happened once**: constructive-retention's RB-15 sweep found
retention was a *step, not a decay curve*, and curve-shaped reporting nearly hid it
(sibling repo, `notebook/notes/acquisition-window.md` — cited as a path rather than
a link, since cross-repo links break CI where only this repo is checked out).
On mathematics, acquisition events will be far sparser than on a 112-instance
synthetic schedule. `W(3)` is the right instinct pointing at this, but it is one
window statistic, not an acquisition-curve concept.

## What the first LLM run changed

[RB-19](../experiments/RB-19-agentic-two-hop-retrieval.md) resolved the immediate
measurement gap on 2026-09-06. At this small scale, per-arm cost did not bite: the
final 192-call run cost US$0.0148. The prior was numerically stable at zero, but
nonce prompts plus an empty store do not test the predicted pretrained-competence
problem, so strain 2 remains untested rather than refuted.

Strain 3 did bite in a mundane but useful form. The hard-reset arm cleared 63/64
probes, yet the whole-run reward is only 0.5625 because 48 training items are
structurally scored zero. Component and held-out metrics recover the result; the
single mean obscures it.

The run also exposed a fourth strain: **an independently sampled stochastic ceiling
is not a fixed ceiling.** The reset arm happened to score 63 probes and the no-reset
arm 61, producing normalised retention 1.033 with a wide `[0.803, 1.309]` CI. That
is acceptable in a dated snapshot but cannot be read like the deterministic ladder.

Most importantly, iterative retrieval answered all 32 two-hop transfer probes. The
current composition rung no longer tests the claimed boundary. Deeper composition,
revision, and aggregation now carry the theory; the phased-ladder calibration gap
([RB-21](../../.tasks/RB-21-phased-reference-ladder.md)) remains separate.

The validity concern is now concrete rather than hypothetical. The first messy,
stochastic SUT did not break the substrate, but it made the independently sampled
ceiling and model-output validity load-bearing. The instrument has therefore been
pointed outside its original deterministic comfort zone; only one model and one
run have been tested.

## Failure mode still open

RB-19 did not test whether pretrained competence makes `P` unpinnable: nonce labels
plus an empty retrieval chain produced a zero floor. If a future real-material run
makes the denominator prompt-sensitive or unstable, that remains a metric-level
rethink rather than a tweak.

## Related

- [ADUS mapping](adus-mapping.md) — the ceiling/slope routing decision these
  strains sit downstream of.
- [The episodic→semantic axis](episodic-semantic-axis.md) — the profile-across-rungs
  reading is another argument against collapsing a run to one mean.

## Changelog

- 2026-09-06: updated predictions with RB-19's first LLM evidence; added the
  stochastic-ceiling strain and recorded that two-hop retrieval closes the current
  composition gap.
- 2026-08-02: created from the pre-publish zoom-out.
