# B14 Open-model judge quality validation

**Priority:** medium
**Blocked by:** nothing
**Touches:** `scorer/`, `tests/`, `docs/metrics.md`, new eval asset(s)

## Context

The LLM-as-judge (`scorer/judge.py`) is the measuring instrument whose verdict
drives **every** retention score. B9 pinned it to a frontier *open* model
(`moonshotai/kimi-k2.6`) on the reasoning that (a) a pinned model keeps scores
comparable across runs, and (b) tool-use/function-calling reliability matters
more here than cost. What was explicitly **not** established is whether an open
model judges *as well as* a closed frontier model (e.g. a Claude judge). Until
that's measured, retention numbers rest on an unvalidated instrument.

This was called out as out-of-scope in B9 and deferred here.

## Goal

Quantify how well the pinned open judge agrees with a stronger reference judge
(and/or human labels) on the judge-eligible question types
(`entity_tracking`, `multi_hop`), so the judge-model choice is a *justified*
measurement parameter rather than an assumption.

## Acceptance criteria

- [ ] A small labelled set of (question, gold, sut_answer, true_verdict) cases
      covering the judge-eligible types, including borderline/paraphrase cases
      (the q3 "three police officers" ≈ "the police" family).
- [ ] Agreement metrics (accuracy / Cohen's κ) of kimi-k2.6 vs a reference judge
      (a Claude judge via OpenRouter) and vs the human labels.
- [ ] A short written finding in `docs/metrics.md`: is the open judge good
      enough, on which question types does it drift, and what's the recommended
      pinned judge as a result.
- [ ] If kimi-k2.6 is found wanting, a recommendation (different pinned model, or
      an ensemble/abstain rule) — not necessarily implemented here.

## Relevant files

- `scorer/judge.py` (the instrument under test)
- `tests/fixtures/fake_judge_responses.yaml` (shape reference for the label set)
- `docs/metrics.md` (B7 — where the finding lives)

## Decisions already made

- Judge model stays **pinned** and recorded as a measurement parameter (B9).
  This task validates the choice; it does not make the judge model free-varying.
