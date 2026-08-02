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
(see that repo's [acquisition window](../../../constructive-retention/notebook/notes/acquisition-window.md)).
On mathematics, acquisition events will be far sparser than on a 112-instance
synthetic schedule. `W(3)` is the right instinct pointing at this, but it is one
window statistic, not an acquisition-curve concept.

## What this implies for priority

**The first LLM measurement ([RB-19](../../.tasks/RB-19-first-agentic-llm-measurement.md))
is the highest-value next thing, ahead of closing the phased-ladder gap
([RB-21](../../.tasks/RB-21-phased-reference-ladder.md)).**

All three strains above are currently *speculation*. The instrument has only ever
been run on systems that are cheap, deterministic and well-behaved. One real,
stochastic, expensive SUT will tell us which strains actually bite and in what
order, and every design decision after that is better informed.

RB-21 is cheap (roughly a day, keyless, CI-able) and closes a gap now stated openly
in three documents — do it, but do not let it delay RB-19.

There is also a validity point in this. The instrument is co-designed with a system
expected to do well on it, **and has only ever been pointed at systems that behave
the way it expects.** That is a narrower validation than the published disclosure
currently implies, and the first messy SUT is a test of the instrument more than of
the SUT.

## The failure mode that would change the assessment

If the first LLM run shows the band normalisation is unstable enough that `P`
cannot be pinned, that is not a metric tweak — it is a rethink of how anything is
normalised, and the moment to reconsider whether normalised retention is the right
headline at all. Judged unlikely, but it is the identifiable failure mode rather
than a vague worry, and it is cheap to find out.

## Related

- [ADUS mapping](adus-mapping.md) — the ceiling/slope routing decision these
  strains sit downstream of.
- [The episodic→semantic axis](episodic-semantic-axis.md) — the profile-across-rungs
  reading is another argument against collapsing a run to one mean.

## Changelog

- 2026-08-02: created from the pre-publish zoom-out.
