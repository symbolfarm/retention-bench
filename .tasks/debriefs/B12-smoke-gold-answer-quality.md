# Debrief: B12 Smoke-task gold-answer quality pass

**Completed:** 2026-05-27
**Commit:** a868ecc

## What shipped

A measurement-validity sweep of the five smoke-test questions in
`tasks/smoke-test/task.yaml`, fixing the exact-match false-negatives without
loosening into false positives:

- **q4** (the flagged one): was `surface_factual`, gold `"a heartbeat"`, with
  an "Answer with a single noun phrase" instruction. Substance-correct answers
  like "the old man's heartbeat" fail exact-match (which strips punctuation and
  case but not articles or synonyms) and — being `surface_factual` — aren't
  rescued by the judge. Reworded to force a single-word answer and changed the
  gold to `"heartbeat"`. The question now asks what *sound* he hears, which
  favours "heartbeat" over the organ "heart".
- **q1**: `surface_factual`, gold `"pale blue"`, previously no answer-form
  constraint. Added "Answer with a two-word color" so the canonical phrase is
  the only natural answer (removes the "blue" / "pale blue film" false-negative
  risk).
- **q2** (`"seven"`, single word), **q3** (`"the police"`, entity_tracking →
  judge), **q5** (`"eighth"`, multi_hop → judge): left unchanged — q2 is
  already a clean article-free single-word fact; q3/q5 route to the judge,
  which handles paraphrase.
- Captured the general authoring guideline in `docs/question-set-spec.md`
  (under the `text` style guide): exact-match golds need a constrained answer
  form + a single canonical article-free answer; phrasing-variable answers
  should use a judge-scored taxonomy, not `exact_match`.

## Descoped / deferred

- Cohort-1 question authoring — explicitly out of scope (smoke-test only).
- Scorer dispatch changes — B3 is locked; this was an asset-only fix.
- A multi-answer/`accepted_answers` mechanism for the smoke `task.yaml`: the
  question-set *spec* already documents `accepted_answers` for exact-match, but
  the MVP smoke schema/scorer only support a single `gold` string. Wiring
  `accepted_answers` into the smoke harness would be a scorer/schema change
  (not asset-only), so "broaden the gold" was off the table here. See
  follow-up below.

## Design decisions

- **Tighten q4, don't re-type it.** The brief offered tighten / broaden /
  re-type. Re-typing to a judge-eligible type was rejected: q4 is genuinely a
  surface fact ("what sound"), and neither judge-eligible type (`entity_tracking`,
  `multi_hop`) honestly describes it — re-typing would mislabel the cognitive
  type the smoke test is meant to exercise, and adding a new judge-eligible
  surface-ish type would touch scorer dispatch (out of scope). Tightening keeps
  q4 an honest exact-match surface fact.
- **q1 reworded even though it wasn't the reported failure.** The brief asked
  to sweep the other `surface_factual` golds for the same smell; q1's
  unconstrained colour answer was the only other real exact-match risk, so it
  got the same answer-form constraint treatment for consistency with q2/q3/q5.
- **Residual ambiguity on q4 accepted as smoke-grade.** "single word" + "sound"
  strongly favours "heartbeat", but a literal reader could still answer
  "beating" or "heart". This is acceptable for a smoke asset whose bar is
  "exercises the pipeline", not publishable data (see the task README). Not
  worth engineering away without the `accepted_answers` mechanism.

## Observations

- The source text never literally says "a heartbeat" — it says "the beating of
  the old man's heart". So the original gold was itself a paraphrase, which is
  partly why exact-match struggled. The new gold "heartbeat" is the canonical
  single-word name for that sound.
- The `sample-output*.md` files under `tasks/smoke-test/` still show the old q4
  gold/phrasing. **Left intentionally** — they are records of what specific
  past runs actually produced; editing them would falsify the run history. Only
  the README's current-asset table was updated.
- The q4 "a heartbeat" references in `tests/test_scorer_judge.py` are hand-built
  records that test the *scorer's* behaviour (no paraphrase-rescue for
  surface_factual), independent of the asset. Left as-is; only refreshed the
  stale comment that called B12 a pending follow-up.

## Follow-ups

### Filed as tasks

None filed automatically — but one candidate surfaced (see below); flagging to
the user rather than filing unilaterally since it overlaps existing seams.

### Drive-by cleanup landed

- Updated the q1/q4 rows in `tasks/smoke-test/README.md` to match the new
  golds (commit a868ecc).
- Refreshed the stale "candidate for a follow-up task" comment in
  `tests/test_scorer_judge.py` to note B12 resolved it in the asset (a868ecc).

### Considered (flagged to user, not yet filed)

- **Wire `accepted_answers` into the smoke `task.yaml` schema + exact-match
  scorer.** The question-set spec already documents it; the MVP scorer ignores
  it. This is the principled long-term fix for terse-gold false-negatives
  (broaden rather than constrain), but it's a scorer/schema change overlapping
  B6/B7 territory, so it shouldn't be slipped in under an asset task.
