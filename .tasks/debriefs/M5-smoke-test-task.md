# Debrief: M5 Smoke-test task definition

**Completed:** 2026-05-20
**Commit:** 0edd1c8

## What shipped

`tasks/smoke-test/` with three files:

- `source.md` — full text of Poe's *The Tell-Tale Heart* (1843), with a
  header comment citing source and confirming public-domain status.
  ~10.5 KB / ~2200 words.
- `task.yaml` — task definition with 5 questions (3 surface_factual,
  1 entity_tracking, 1 multi_hop) inline, 5-event sequence
  (prior → read → ceiling → reset → retention@1). Validates against
  the M1 task loader.
- `README.md` — one paragraph each on what this is, what it isn't
  (not a cohort-1 asset), source provenance, question coverage, and
  the inline-questions decision.

Validated end-to-end via `harness.task_loader.load_task` — schema and
semantic validation both pass.

## Descoped / deferred

- **Separate `questions.yaml` file.** Acceptance-criterion 2 listed
  this as a separate file; see "Design decisions" below.
- **Thematic / retroactive question types.** Out-of-scope per the
  task brief; reserved for cohort-1 question sets.
- **LLM-judge gold schemas.** Plain-string golds per M1 schema; richer
  gold-answer schemas land with backlog item B3.

## Design decisions

- **Inlined questions in `task.yaml` rather than splitting to
  `questions.yaml`.** Acceptance-criterion 2 listed `questions.yaml`
  as a separate file. The M1 schema doc (`docs/task-definition-schema.md`)
  calls the split "optional but recommended once they grow," but the
  M1 loader (`harness/task_loader.py`) has no cross-file include
  support — `questions:` is parsed only from the inline list under
  `task.yaml`. Three options were on the table (inline-only,
  inline-plus-duplicate-copy, extend-loader); confirmed inline-only
  with Toby before writing. Surface-area is small (5 questions);
  loader change can land properly when a real task set warrants it.

- **Source text choice: Poe's *The Tell-Tale Heart* (1843).** The
  schema doc's worked example uses Kafka's *Metamorphosis* — equally
  valid PD choice, but using a different text in the actual fixture
  avoids any impression the worked example was copy-pasted into
  production. Tell-Tale Heart is short (~2200 words), self-contained,
  high-pretraining-contamination (good for non-trivial `P`), and has
  clean entity/event structure for the question taxonomy. No
  translation copyright issues (original English).

- **Included the full short story rather than a 1–2 page excerpt.**
  The brief said "~1–2 pages." Tell-Tale Heart is ~4 printed pages but
  ~10 KB plain text. Splitting it mid-narrative would have made
  multi-hop and entity-tracking questions awkward (e.g. the q5
  "eighth night" answer depends on text in two distinct passages).
  Full-text inclusion is cleaner and still well within any practical
  context window. Decision is reversible — truncate later if the
  smoke test's read-time becomes a problem.

- **Question prompts include format hints** ("Answer with a single
  word," "Answer with a single ordinal word," etc.). Without them,
  exact-match scoring under M6 would false-negative constantly on
  verbose LLM replies. The hints are a smoke-test-specific
  affordance, not a precedent for cohort-1 question authoring; real
  cohort-1 questions will go through an LLM-judge scorer (B3) where
  format hints aren't needed.

- **q5 ("eighth night") chosen as the multi_hop question** because it
  requires combining two facts ("seven nights of watching" + "the
  next night, he killed him") into a derived ordinal. Other candidate
  multi-hops (e.g. "why does the narrator confess?") had golds that
  resisted tight string form — a problem under exact-match scoring.

## Observations

- The schema doc's worked example for the smoke-test shape (lines
  118–172 of `docs/task-definition-schema.md`) is detailed enough
  that it effectively pre-specified the structure. Real judgment
  was confined to (a) source-text selection, (b) the
  inline-vs-split-questions resolution, and (c) wording the
  questions so exact-match scoring won't immediately fail. The brief
  was well-scoped.

- **The inline-vs-split discrepancy was inherited silently from M1.**
  M1's debrief doesn't flag that the loader and the schema-doc prose
  disagree about cross-file question references. Caught here because
  the M5 acceptance criteria explicitly listed `questions.yaml` as a
  separate file. Worth a one-line note in `docs/task-definition-schema.md`
  if/when it's next edited — see follow-up F1 below.

- **Format-hinted prompts will affect `prior` measurements.** A
  pretraining-only `prior` probe sees the question with its format
  hint and may answer in the requested form even without seeing the
  text. That's a feature for smoke-testing the scorer (matches
  align), but worth noting if anyone reads `P` values from this run
  as substantive. Documented in `README.md`.

- **No fixture-tests for `tasks/smoke-test/`.** There's no
  automated test that re-validates this directory on every CI run.
  If someone later edits the task without re-running M5/M6/M7,
  drift could creep in. Probably not worth a test for a single
  fixture; revisit if more task fixtures accumulate.

## Follow-ups

### Filed as tasks

None. The candidates below are either drive-bys (none landed),
genuinely backlog material that already exists, or drops.

### Considered and dropped

- **Extend M1 loader to support `questions: { path: ... }` or an
  `!include` directive.** Would resolve the schema-doc-vs-loader
  inconsistency cleanly but adds real surface area to a v1-locked
  schema. With only one task fixture in the tree, premature.
  Re-raise if/when question sets cross ~20 entries or a second
  fixture needs to share question banks.

- **Patch `docs/task-definition-schema.md` to remove the "optional
  but recommended" line about splitting questions, since the loader
  doesn't support it.** Considered as a drive-by but it's a doc
  change touching an M1-locked spec; would need its own commit
  message and ideally re-validation of M1's debrief invariants.
  Leaving it for whoever next edits that doc. Mentioned in README so
  future-me has a thread to pull.

- **Add a fixture-validation test in `tests/`.** One file, one task,
  no real risk of drift in the MVP timeframe. Not worth the
  weight; revisit post-MVP if more fixtures land.

- **Use a less famous text to keep `P` low.** Tempting, but the
  task brief specifically called for a contaminated text so
  `(R − P) / (C − P)` is observable. Following the brief.
