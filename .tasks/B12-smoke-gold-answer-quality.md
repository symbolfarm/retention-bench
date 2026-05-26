# B12 Smoke-task gold-answer quality pass

**Priority:** low
**Blocked by:** nothing
**Touches:** `tasks/smoke-test/task.yaml`, possibly `docs/question-set-spec.md`

## Context

The B3 judge work surfaced a question-authoring issue, not a scorer issue:
smoke-test q4's gold answer `"a heartbeat"` is too terse. A substance-correct
SUT answer like "The old man's heartbeat" fails exact-match — and because q4 is
typed `surface_factual`, the locked B3 dispatch routes it to exact-match
(bypassing the judge by design), so it stays excluded even under
`--scorer judge`. The fix belongs in the *task asset*, not the scorer: either
tighten the question so the terse gold is the only natural answer, broaden the
gold/acceptable-answers, or re-type the question if it isn't really a clean
surface fact.

This is a measurement-validity call (what counts as correct), so it shouldn't
be changed unilaterally inside a scorer — hence a separate task. Worth a sweep
of the *other* smoke questions for the same terse-gold smell while here.

## Goal

Smoke-test gold answers are phrased so that exact-match on `surface_factual`
questions doesn't reject substance-correct answers — without loosening into
false positives.

## Acceptance criteria

- [ ] q4 ("a heartbeat") resolved: tighten question, broaden gold, or re-type.
- [ ] Other smoke `surface_factual` golds swept for the same issue.
- [ ] Rationale noted (validity: why each gold is the right discriminator).
- [ ] If a general guideline emerges, capture it in `docs/question-set-spec.md`.

## Relevant files

- `tasks/smoke-test/task.yaml` — questions + gold answers.
- `runs/smoke-test-2026-05-25T12-51-56Z-34ca7c/questions.jsonl` — the live run
  showing the false-negatives.
- `docs/question-set-spec.md` — where any authoring guideline lives.

## Out of scope

- Cohort-1 question authoring (orthogonal; this is smoke-test only).
- Changing scorer dispatch behaviour (B3 is locked; this is an asset fix).
