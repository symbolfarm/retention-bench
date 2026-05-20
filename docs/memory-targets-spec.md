---
title: Memory-targets companion spec
project: continual-learning-eval
status: spec v0.1 (Turn 6 of [[design-dialogue]], 2026-05-13)
audience: author models producing `memory-targets.md` alongside their novella; question-author models consuming it
tags: [spec, book-track, memory-targets]
---

# Memory-targets companion spec

Format for the `memory-targets.md` file that ships with every novella in the CL-eval book track. This document is **the contract between the novella author and the question-author**. The author plants targets in the novella and declares them here; the question-author consumes this file (plus the novella itself) to write questions.

Constraints:

- The file must be parseable by a downstream tool. Adhere to the section structure exactly.
- Every claim in this file must be *verifiable from the novella text*. Do not declare a target that the text does not actually contain.
- Conversely, every structural-requirement floor from [`book-spec.md`](./book-spec.md) (≥ 40 surface facts, ≥ 5 entity arcs, ≥ 6 multi-hop chains, ≥ 4 retro facts, ≥ 3 thematic threads) must be visible in this file as the corresponding count.

## File structure (in order)

1. YAML frontmatter
2. `## 1. Summary`
3. `## 2. Surface-factual targets`
4. `## 3. Entity arcs`
5. `## 4. Multi-hop chains`
6. `## 5. Retroactively-relevant facts`
7. `## 6. Thematic threads`
8. `## 7. Coverage check`

Each section's format is specified below.

## Frontmatter

```yaml
---
novella_title: <title, matching novella.md frontmatter>
author_model: <model name, matching novella.md>
seed_triple:
  setting: "<setting tilt>"
  tone:    "<tone tilt>"
  form:    "<form tilt>"
  forbidden: ["<forbidden 1>", "<forbidden 2>"]
chapter_count: 10
total_targets:
  surface_facts: <integer>
  entity_arcs: <integer>
  multi_hop_chains: <integer>
  retro_facts: <integer>
  thematic_threads: <integer>
---
```

## 1. Summary

A 4–8 sentence plain-prose summary of the novella. Used by the question-author as orientation. Do not include this in `novella.md`.

## 2. Surface-factual targets

A markdown table, one row per surface fact:

| id | chapter | fact | source span |
|---|---|---|---|
| sf-001 | 1 | The lighthouse keeper's name is Idris Vaal. | "Idris Vaal had kept the light for twenty-three years…" |
| sf-002 | 1 | The lighthouse stands seventeen metres tall. | "the seventeen-metre tower…" |
| sf-003 | 2 | The fishing boat is named *Almara*. | "the *Almara* was the last to return…" |
| … | | | |

**`id`** is `sf-NNN` with three-digit zero-padded ordering.
**`fact`** is a single declarative sentence stating the fact in its canonical form (what a correct answer would assert).
**`source span`** is a short literal quote from the novella demonstrating the fact. The quote must appear verbatim in the novella text. Use ellipses for trimming if needed but the quoted phrase must be findable by string search.

Distribute ≥ 4 surface facts per chapter. ≥ 40 total.

## 3. Entity arcs

One subsection per entity arc, format:

```
### ea-N — <entity name>

- type: character | object | place | institution | other
- introduced: chapter <N>
- chapters_appearing: [<N>, <N>, <N>, …]
- arc:
  - chapter <N>: <state at this point — one sentence>
  - chapter <N>: <state at this point — one sentence>
  - chapter <N>: <state at this point — one sentence>
- final_state: <what is true of this entity by end of novella>
- source_anchors: <list of short quotes, one per arc point, verbatim from text>
```

≥ 5 entity arcs total. Each arc spans ≥ 3 chapters.

## 4. Multi-hop chains

One subsection per chain, format:

```
### mh-N — <one-line description of the multi-hop>

- chapters_required: [<N>, <N>, …]   # ≥ 2 chapters
- chain:
  - chapter <N> provides: <fact from this chapter — one sentence>
  - chapter <N> provides: <fact from this chapter — one sentence>
- synthesized_fact: <the conclusion that follows only from combining the above>
- source_anchors: <one short verbatim quote per chapter in the chain>
- intended_question_shape: <one sentence describing what kind of question would draw on this chain — for the question-author's orientation, not as a finished question>
```

≥ 6 chains total. Span a range of chapter-pair distances. At least 2 chains should require ≥ 3 chapters (deep multi-hops).

## 5. Retroactively-relevant facts

One subsection per retro fact, format:

```
### rr-N — <one-line description>

- introduced_in: chapter <N (1–4)>
- cued_in: chapter <N (6–10)>
- fact: <the early-incidental detail, as a declarative sentence>
- relevance: <what the late chapter reveals about why this matters>
- early_source: "<verbatim quote from the introducing chapter>"
- late_source: "<verbatim quote from the cueing chapter>"
- camouflage_note: <one sentence on what makes the early occurrence look incidental — useful to the question-author for judging which facts are genuinely retro vs. flagged>
```

≥ 4 retro facts. Early occurrences must be in chapters 1–4; cues in chapters 6–10.

## 6. Thematic threads

One subsection per thread, format:

```
### tt-N — <thread name, 1–3 words>

- chapters_appearing: [<N>, <N>, <N>, <N>, …]   # ≥ 4 chapters
- treatment_evolution:
  - chapter <N>: <how the thread appears here — one sentence>
  - chapter <N>: <how the thread appears here — one sentence>
  - chapter <N>: <how the thread appears here — one sentence>
  - …
- summary: <one sentence on what the thread, taken as a whole, says or shows>
- source_anchors: <one short verbatim quote per chapter appearance>
- intended_question_shape: <one sentence on what synthesis the question-author could draw from this thread>
```

≥ 3 thematic threads. Each spans ≥ 4 chapters.

## 7. Coverage check

A summary table verifying floors are met:

| Target type | Floor | Actual |
|---|---|---|
| Surface facts | ≥ 40 | <count> |
| Surface facts per chapter (min) | ≥ 4 | <min across chapters> |
| Entity arcs | ≥ 5 | <count> |
| Multi-hop chains | ≥ 6 | <count> |
| Retro facts | ≥ 4 | <count> |
| Thematic threads | ≥ 3 | <count> |

Plus a coverage-by-chapter table:

| Chapter | Surface facts | Entity-arc points | Multi-hop contributions | Retro early | Retro cue | Thematic appearances |
|---|---|---|---|---|---|---|
| 1 | <n> | <n> | <n> | <n> | <n> | <n> |
| … | | | | | | |
| 10 | <n> | <n> | <n> | <n> | <n> | <n> |

These tables let a reviewer (and the question-author) confirm distribution at a glance.

## Style notes

- One declarative sentence per `fact` / `synthesized_fact` / arc point. No hedging, no elaboration. The question-author needs the canonical form.
- Source anchors should be **as short as possible while still being findable in the novella by string search**. Three to fifteen words is typical.
- IDs (`sf-NNN`, `ea-N`, etc.) are stable. The question-author will reference them.
- Do not editorialise. This is a contract, not commentary.

## What this file is not

- Not a plot summary in narrative form (apart from §1's short orientation paragraph).
- Not a list of questions — that's `question-set-spec.md`.
- Not a record of every fact in the novella — only the planted, scored-target facts.
- Not a writeup of authorial intent. The question-author should not need to know *why* a thread was chosen, only *what* and *where*.

## Cross-references

- [`book-spec.md`](./book-spec.md) — the brief that authors the novella + this companion.
- [`question-set-spec.md`](./question-set-spec.md) — the downstream spec the question-author follows.
