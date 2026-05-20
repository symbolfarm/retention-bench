# M5 Smoke-test task definition

**Priority:** medium
**Blocked by:** M1
**Touches:** `tasks/smoke-test/` (new), possibly `tests/fixtures/`

## Context

A toy book-track task for end-to-end smoke testing. Explicitly NOT a cohort-1 asset (cohort-1 is the AI-generated novella pipeline, blocked on Toby's sign-off). The smoke test exists to exercise the full pipeline — multi-question `QUIZ` events, all three probe types (`prior`/`ceiling`/`retention`), at least one `RESET` — with a text the no-state SUT will plausibly partially-know from pretraining, so the `P > 0` baseline is interesting.

Decision (Toby, 2026-05-20): use a **public-domain excerpt**. Recommended pick: opening of a well-known short story (e.g. Kafka's *Metamorphosis*, Borges' *The Library of Babel*, or Chekhov's *The Lady with the Dog*). Pretraining contamination on these is high — exactly what we want, because it makes `P` non-trivial and the `(R−P)/(C−P)` normalisation observable.

## Goal

A self-contained `tasks/smoke-test/` directory with: a public-domain text excerpt, a question set (~5 questions across question-type categories, three probes per question), and a task-definition YAML wiring them into a `READ`/`QUIZ`/`RESET` sequence that exercises all three probes.

## Acceptance criteria

- [ ] `tasks/smoke-test/source.md` — public-domain text (~1–2 pages). Cite source + confirm public-domain status in a header comment.
- [ ] `tasks/smoke-test/questions.yaml` — ~5 questions with `(question_id, question_text, gold_answer, question_type, material_ref)` per M1 schema. Cover at least: surface-factual, entity-tracking, multi-hop. (Thematic/retroactive can wait for cohort-1.)
- [ ] `tasks/smoke-test/task.yaml` — task definition per M1 schema, wiring an event sequence roughly:
  ```
  QUIZ(all questions, prior)
  READ(source.md)
  QUIZ(all questions, ceiling)
  RESET
  QUIZ(all questions, retention@1)
  ```
- [ ] `tasks/smoke-test/README.md` — one paragraph explaining what this is, what it's for, and what it explicitly is NOT (not cohort-1, not a real benchmark task).
- [ ] Task definition validates against the M1 schema.

## Relevant files

- `docs/task-definition-schema.md` (from M1) — the contract this fixture must satisfy.
- `docs/tasks.md` — book-track structure, probe semantics, question taxonomy.
- `docs/question-set-spec.md` — fuller question-design guidance (use as inspiration; this is a toy set, not a cohort-quality set).

## Decisions already made

- Public-domain excerpt over hand-authored or AI-generated (Toby, 2026-05-20).
- Smoke-test, not cohort-1. Quality bar is "exercises the pipeline," not "produces publishable retention data."
- Exact-match gold answers for the surface-factual questions; short open-ended gold for the others (LLM-judge scoring comes later as B3, but for now exact-match is the scorer per M6, so prefer questions with unambiguous short answers).

## Out of scope

- Cohort-1 novella generation (B8).
- Thematic/retroactive questions (cohort-1 work; smoke test only needs basic taxonomy coverage).
- LLM-judge gold criteria (B3 will retrofit when LLM-judge scorer lands).
- Multi-novella runs.

## Notes for the implementer

- Pick the source text first; let the question set follow naturally from what's in the text. Don't try to force the full taxonomy onto a short excerpt — surface-factual + entity-tracking + one multi-hop is plenty.
- If the chosen excerpt is too well-known (e.g. opening of *Pride and Prejudice*), `P` will saturate and `(R−P)/(C−P)` will be ill-defined for some questions. That's OK for a smoke test — it's also a useful real signal that the contamination measurement works. Note it in the README.
- Make the gold answers tight strings (one word or short phrase where possible) so exact-match scoring in M6 isn't constantly false-negative.
