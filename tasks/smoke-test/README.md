# Smoke-test task

A toy book-track task whose only job is to exercise the full harness +
SUT + scorer pipeline end-to-end. Five short-answer questions over a
short public-domain source text, with one `RESET` so the run produces
all three probes (`prior`, `ceiling`, `retention@1`).

This is **not** a cohort-1 benchmark asset. Quality bar is "the
pipeline runs and the trace is well-formed," not "this measures
retention in any scientifically meaningful way." Cohort-1 work is
tracked separately as B8 and remains blocked on sign-off.

## Source

Edgar Allan Poe, *The Tell-Tale Heart* (1843). Public domain in the
United States and worldwide (Poe died 1849; no translator). The full
short story is reproduced in `source.md`; provenance and PD status are
documented in the header comment of that file.

The story was chosen because pretraining contamination on canonical
19th-century English-language fiction is high — which is exactly what
we want for a smoke test. A non-trivial `P` (prior-knowledge baseline)
makes the `(R − P) / (C − P)` retention normalisation observable on a
real run. If `P` saturates (e.g. the no-state SUT answers most questions
correctly without ever seeing the text), the retention curve is
ill-defined for those questions — that's a useful smoke signal in
itself, not a bug. See `docs/metrics.md` for the normalisation
definition.

## Files

| File | Purpose |
|---|---|
| `task.yaml` | Task definition (materials + questions + event sequence) |
| `source.md` | The Poe text, with provenance header |
| `README.md` | This file |

Questions live inline in `task.yaml`. The M1 task-definition schema
mentions splitting questions into a separate `questions.yaml` as
"optional but recommended once they grow"; the M1 loader does not
currently support cross-file question references, so for a 5-question
fixture inlining is simpler. Revisit when a real task exceeds ~20
questions.

## Event sequence

```
QUIZ(q1..q5, prior)
READ(source)
QUIZ(q1..q5, ceiling)
RESET
QUIZ(q1..q5, retention, k=1)
```

Yields 5 events + 15 per-question records (5 questions × 3 probes).

## Question coverage

| ID | Type | Notes |
|---|---|---|
| q1 | surface_factual | The vulture eye — two-word colour gold (`pale blue`) |
| q2 | surface_factual | Number of nights of watching — single-word gold |
| q3 | entity_tracking | Who arrives at the end — single noun phrase |
| q4 | surface_factual | The sound that drives the confession — single-word gold (`heartbeat`) |
| q5 | multi_hop | Combines "seven nights of watching" + "the next night" → "eighth" |

Thematic and retroactive question types are out of scope for the smoke
test; they're more appropriate for cohort-1 question sets where richer
gold-answer schemas (LLM-judge etc., backlog item B3) will be wired up.

Gold answers are deliberately tight (one word or short phrase) so the
M6 exact-match scorer doesn't constantly false-negative. The prompts
nudge the SUT toward short replies for the same reason.
