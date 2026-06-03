# B15 Benchmark validity: prior-saturation & question-type separation

**Priority:** low
**Blocked by:** nothing
**Touches:** `docs/metrics.md`, `scorer/aggregate.py`, analysis tooling (`unknown`)

## Context

Two validity concerns surfaced in discussion (2026-06-03) that the harness does
not currently account for or check. Both are about whether the instrument is
measuring *understanding-transfer* (the real target — see the
episodic→understanding research frame) versus an artifact, and whether it stays
valid as base models improve. Recording them so they inform the synthetic-data
track (B5/B8) and the first real curve-producing runs, rather than evaporating.

**(1) Prior-saturation shelf-life.** The `C≈P` exclusion (drop a question when
ceiling ≈ prior) is correct — but it makes the benchmark's *effective n*
model-dependent. The B9 smoke run showed it starkly: 4 of 5 questions excluded,
`n_usable=1`, because a capable base model already knew the answers (`prior≈1`).
As models improve, more world-knowledge questions saturate priors and fall out
the bottom. Implication: a **renewable supply of material the model provably
hasn't seen** isn't a nice-to-have for synth-gen — it's load-bearing for the
benchmark staying able to measure anything at all. This reframes the priority of
the synthetic-data track (B5/B8) from "variety" to "validity."

**(2) Stenography vs understanding (question-type separation).** notes_llm
retains by writing cumulative notes to `DIR` — externalised episodic memory done
competently. If it posts a strong retention curve, that may just mean "facts
survive in notes," which says nothing about whether *understanding* transferred.
The interesting signal is whether its curve **separates by `question_type`**:
high on `surface_factual` (trivially carried by notes), collapsing on `multi_hop`
(requires synthesis the notes don't literally contain). A flat-high curve across
all types would be a *warning* that the benchmark is rewarding stenography, not
comprehension.

## Goal

Decide and document how the benchmark stays valid as base models improve, and
make question-type-separated retention a first-class reported quantity so the
stenography-vs-understanding distinction is visible in every run.

## Acceptance criteria

- [ ] `docs/metrics.md` records the prior-saturation argument and its
      consequence for synth-gen priorities (material novelty as a validity
      requirement, with a target for keeping `prior` low).
- [ ] Retention curves are reported **broken down by `question_type`**, not just
      pooled — so `surface_factual` vs `multi_hop` separation is legible per run.
- [ ] A documented interpretation rule: flat-high-across-types = stenography
      smell; separation (esp. weak `multi_hop`) = the understanding-transfer
      signal we want.
- [ ] Cross-references added so B5/B8 (synth-gen) inherit the novelty requirement.

## Relevant files

- `scorer/aggregate.py` (per-question-type breakdown of the curve)
- `docs/metrics.md` (B7 — validity narrative lives here)

## Decisions already made

- The `C≈P` exclusion stays — it's the right call (a benchmark that returns null
  on no-signal questions is trustworthy). B15 is about its *consequences*, not
  removing it.
