---
title: Question-set spec
project: continual-learning-eval
status: spec v0.1 (Turn 6 of [[design-dialogue]], 2026-05-13)
audience: question-author models consuming novella.md + memory-targets.md and producing question-set.yaml
tags: [spec, book-track, question-set]
---

# Question-set spec

Format for the question set produced **per novella** by a question-author model. The question-author is a *different model* from the novella author (a cheap validity property — author-of-asset has a mild incentive to plant easy facts; we decouple).

## Inputs the question-author receives

- `novella.md` — the full novella text.
- `memory-targets.md` — the planted-targets companion ([`memory-targets-spec.md`](./memory-targets-spec.md)).

The question-author **must not** receive `book-spec.md` (which contains the per-novella diversity seed and any other meta-information that could leak into questions). If the diversity-seed phrases happen to appear in the novella text, that is expected; the question-author working from the text alone cannot tell which were seeded.

## Output: `question-set.yaml`

A single YAML file. Top-level structure:

```yaml
novella_title: <matches novella.md>
question_author_model: <model name>
created: <ISO 8601 date>
questions:
  - id: q-001
    text: …
    gold_answer: …
    taxonomy: surface | entity | multi_hop | thematic | retro
    source_chapters: [<N>, …]
    target_refs: [<ids from memory-targets.md>]
    probe_schedule: [prior, ceiling, retention]
    scoring:
      rule: exact_match | rubric | structural
      ...
    notes: <optional one-line note for judges>
  - id: q-002
    …
```

## Per-question fields

### `id`
String, format `q-NNN`. Three-digit zero-padded, stable. Used by the harness to track per-question scores `P`, `C`, `R(k)`.

### `text`
The question as it will be delivered to the SUT. One or a few sentences. Self-contained — the SUT will see this text inside a `STAGE_INPUT` with no additional context.

Style guide:
- Direct questions, not riddles.
- For surface facts: paraphrase the novella's wording, do not quote it directly (a verbatim-cache strategy should not auto-match the question). Example: novella says "Idris Vaal had kept the light for twenty-three years." Question: "How long had the lighthouse keeper held his post?" — not "How long had Idris Vaal kept the light?"
- For multi-hop and synthesis questions: phrase the question so the answer requires the synthesis, not just one chapter's content. Avoid "according to chapter N" framings; the SUT does not navigate by chapter index.
- Don't reveal which probe a question is for. The same question text is used across `prior`, `ceiling`, and `retention` probes by default.
- For `exact_match`-scored questions, constrain the answer form so substance-correct answers can't vary in phrasing — exact-match has no judge to rescue paraphrase. The gold must be the single canonical short answer with no leading article (matching strips punctuation and case but **not** articles or synonyms, so "a heartbeat" ≠ "the old man's heartbeat"). Pin the form in the question text ("Answer with a single word", "Answer with a two-word colour") and pick a gold the constraint actually yields. Corollary: if the faithful answer legitimately varies in phrasing, the question is not a clean exact-match fact — give it a judge-scored taxonomy (`entity` / `multi_hop` with `rubric`), not `exact_match`. (Lesson from the smoke-test q4 "a heartbeat" false-negative; see B12 debrief.)

### `gold_answer`
The canonical answer. For exact-match scoring this is the literal target string (case-insensitive match by default; specify if case matters). For rubric scoring this is a short canonical answer plus pointers to the rubric. For structural scoring this is the canonical structure (e.g., an ordered list of points).

### `taxonomy`
One of:
- `surface` — single-chapter atomic fact.
- `entity` — entity-tracking, state over time.
- `multi_hop` — requires information from ≥ 2 chapters.
- `thematic` — synthesis / motif / argument; open-ended.
- `retro` — retroactively-relevant; the answer is an early-incidental fact whose relevance is cued by a later chapter.

### `source_chapters`
List of chapter numbers (1–10) the question draws on. Used by the harness to compute the relevant `k` for retention probes (`k` = number of `RESET`s between the latest required chapter's `READ` and the `QUIZ`).

### `target_refs`
List of IDs from `memory-targets.md` this question draws on (e.g., `[sf-007, mh-002]`). Required: every question must reference at least one target. This makes coverage analysis trivial and lets a reviewer check that no scored question is unplanted.

### `probe_schedule`
A list specifying which probes use this question. Default: `[prior, ceiling, retention]` (all three).

- A question must have `prior` *unless* it is a `thematic` question that is too open-ended to answer cold (in which case `prior` may be omitted with an explanatory note; the question contributes to `R` but not to normalised retention).
- A question must have `ceiling` *unless* its source chapters span the entire novella and there is no single SUT-process span where all required chapters are simultaneously in-state (rare; declare in `notes`).
- A question must have `retention` to count toward the headline metric.

The harness places probe events according to the run's event sequence (see [`worked-example-book-track.md`](./worked-example-book-track.md)).

### `scoring`
A nested block. Three rules:

**`exact_match`** (typical for `surface`, some `entity`):
```yaml
scoring:
  rule: exact_match
  accepted_answers: [<string>, <string>, …]   # equivalent canonical forms
  case_sensitive: false
  strip_punctuation: true
```

**`rubric`** (typical for `thematic`, open `multi_hop`, open `entity`):
```yaml
scoring:
  rule: rubric
  criteria:
    - <criterion 1, one sentence>
    - <criterion 2, one sentence>
    - <criterion 3, one sentence>
  scoring_band: continuous   # or: discrete [0, 0.5, 1.0]
  judge_count: 3
```

**`structural`** (for ordered-list / set / structured answers):
```yaml
scoring:
  rule: structural
  expected_form: ordered_list | unordered_set | mapping
  expected_items: [<canonical items>]
  match_rule: fuzzy   # or: strict
  partial_credit: true
```

### `notes`
Optional one-line note for judges or for downstream reviewers. Examples: "answer accepted in metres or feet", "synthesise across the two parallel arcs of Vaal and Marle".

## Question count budgets

For one novella (10 chapters, structural floors from `book-spec.md`):

| Taxonomy | Min | Target |
|---|---|---|
| `surface`   | 40 | 50  (≈ 5/chapter) |
| `entity`    |  8 | 12  (≈ 2/arc × 5–6 arcs) |
| `multi_hop` |  6 | 10  (≥ 1 per declared chain, sometimes 2) |
| `retro`     |  4 |  6  (1–2 per declared retro fact) |
| `thematic`  |  4 |  6  (1–2 per declared thread, plus 1–2 whole-text synthesis) |
| **Total**   | 62 | 84 |

Per-cohort, 4 novellas × ~84 questions ≈ 336 questions. At ~32 events per novella per seed × 3 seeds ≈ ~96 events per novella per cohort run; question budget is not the binding constraint, asset diversity is.

## Validity checks (must hold)

The question-author is responsible for these. A reviewer pass will spot-check.

1. **No question is answerable from its own text alone.** A question that telegraphs the answer is invalid.
2. **No question requires information not in the novella.** Every answer is derivable from the text (with `memory-targets.md` as the canonical reference).
3. **No question quotes the novella verbatim.** Paraphrase. (Brief technical terms — a character's name, a place name — are fine.)
4. **Every question references ≥ 1 `target_refs`.** No unplanted questions.
5. **`source_chapters` is accurate.** Includes every chapter required for a correct answer; does not pad with chapters that are merely tangentially relevant. (Used by the harness for `k` calculation — if it's wrong, the metric is wrong.)
6. **Multi-hop questions actually require ≥ 2 chapters.** If a strong reader could answer from one chapter alone, the question is mis-categorised.
7. **Retro questions camouflage the early fact.** The question must be phrased in terms of the *late* cue (the moment when the fact becomes relevant), not the early occurrence. The SUT must be able to answer because it noted the early fact, not because the question pointed at it.
8. **Thematic questions do not telegraph the thread name.** Ask about the thing the thread does or shows; don't name the thread in the question.

## What the question-author does not do

- Not designing the event sequence — the harness does that, per [`tasks.md`](./tasks.md) and [`worked-example-book-track.md`](./worked-example-book-track.md).
- Not deciding which novellas are in the cohort — that's an operator-level decision.
- Not modifying `novella.md` or `memory-targets.md`. If a target appears to have a bug (e.g., the source quote doesn't match the text), flag it in a separate `questions-flags.md` and stop; the novella author or operator resolves.
- Not writing more than the structural budget unless target counts overrun (e.g., a novella that planted 50 surface facts instead of 40 may yield more surface questions).

## Hand-off

Deliver `question-set.yaml` in the same directory as the novella (`cohort-1/novella-3/question-set.yaml`). A reviewer pass checks validity items 1–8 and the per-taxonomy budgets.

## Cross-references

- [`book-spec.md`](./book-spec.md) — the novella brief (the question-author **does not** receive this).
- [`memory-targets-spec.md`](./memory-targets-spec.md) — the question-author's primary input alongside the novella.
- [`tasks.md`](./tasks.md) — Track 1 structure and probe semantics.
- [`metrics.md`](./metrics.md) — how `P`, `C`, `R(k)` flow into normalised retention.
- [`worked-example-book-track.md`](./worked-example-book-track.md) — concrete event sequence that consumes this question set.
