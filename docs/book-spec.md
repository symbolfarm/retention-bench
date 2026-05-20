---
title: Book spec — first-cohort novellas for the CL-eval book track
project: continual-learning-eval
status: spec v0.1 (Turn 6 of [[design-dialogue]], 2026-05-13)
audience: external author models (Claude, GPT-class, Gemini, open-weights — N=3–4 in parallel)
tags: [spec, book-track, farming-brief]
---

# Book spec

This document is the brief handed to an **author model** that produces one novella for the [continual-learning-eval](../README.md) book track. The output is two files: `novella.md` and `memory-targets.md` (the latter per [`memory-targets-spec.md`](./memory-targets-spec.md)). The question set is generated *separately*, by a different model, from the novella + memory-targets only — see [`question-set-spec.md`](./question-set-spec.md). The author model **must not** generate the question set.

A first cohort of N=3–4 novellas is run in parallel across different model families to give cross-asset stratification (per [`validity.md`](./validity.md) Confound 1). Each author model receives the same `book-spec.md` plus a per-novella **diversity seed** (below).

## Purpose, in one paragraph

The eval measures how well an LLM-agent's memory architecture preserves task-relevant information across discontinuities (process restarts). Each novella is one *asset* — the SUT will read it chapter-by-chapter, be reset between sections, and be quizzed about its content at varying numbers of resets after the relevant chapter was delivered. Headline metric is per-question `(R − P) / (C − P)` (retention minus prior, normalised by capability ceiling). Your novella's job is to be (a) original enough that the prior `P` is low, (b) structurally rich enough that the capability ceiling `C` is high, and (c) full of the kinds of facts and threads that distinguish broad memory from narrow memory after several resets.

## What you produce

Two files, both UTF-8 markdown.

### 1. `novella.md` — the text itself

- **Length:** 10 chapters of approximately 1 000–2 000 words each. Total novella length 12 000–20 000 words. Hard floor: every chapter ≥ 800 words. Hard ceiling: every chapter ≤ 2 500 words.
- **Chapter delimiters:** each chapter starts with a heading exactly of the form `## Chapter N — <title>` where `N ∈ {1, 2, …, 10}` and `<title>` is your chosen chapter title. No prologue, no epilogue, no front-matter beyond the title block below.
- **Front-matter:** a YAML frontmatter block at the top of the file:
  ```yaml
  ---
  title: <your novella's title>
  author_model: <the model that wrote this, e.g. "Claude Opus 4.7" / "GPT-5" / "Gemini-2.5-Pro" / "Llama-4-Maverick">
  seed_triple:
    setting: "<the setting tilt from the brief>"
    tone:    "<the tone tilt from the brief>"
    form:    "<the form tilt from the brief>"
    forbidden: ["<forbidden default 1>", "<forbidden default 2>"]
  word_count_estimate: <integer>
  ---
  ```
- **No metadata leak in body text.** Do not mention that this is for an eval, do not reference memory benchmarks, do not name any AI model. The text should read as a stand-alone novella.

### 2. `memory-targets.md` — the planted-targets companion

A structured document declaring what you planted where, conforming to [`memory-targets-spec.md`](./memory-targets-spec.md). This is what the question-author model will consume to write questions. Treat it as the contract between the two roles.

## Structural requirements (what the eval needs)

Your novella must contain, across its 10 chapters:

- **≥ 40 surface-factual targets**, roughly 4 per chapter. These are specific, named, checkable facts — a colour, a number, a name, a date in your novella's world, a piece of equipment, a relationship. Avoid "facts" that can be re-derived from broader narrative context.
- **≥ 5 entity arcs.** A named character, object, place, or institution whose state changes meaningfully over ≥ 3 chapters. Each arc has a beginning state, intermediate state(s), and end state — all anchored in specific text.
- **≥ 6 multi-hop chains.** Pieces of information that cannot be answered from any single chapter — answering requires combining content from ≥ 2 specific chapters. Across the 6, span a range of chapter-pair distances (some adjacent, some with several chapters between them).
- **≥ 4 retroactively-relevant facts.** A fact introduced as an incidental detail in an early chapter (1–4), whose significance is only revealed by a later chapter (6–10). The early occurrence should look like background detail — not flagged, not emphasised. The late chapter should make it matter.
- **≥ 3 thematic threads.** Motifs, images, ideas, or arguments that recur across ≥ 4 chapters with evolving treatment. The thematic content should be inferable from the text but not stated directly.
- **A meaningful final-chapter synthesis.** Chapter 10 should resolve or transform at least one entity arc, at least one thematic thread, and at least one retroactively-relevant fact. The novella's ending must reward whole-text memory, not just chapter-10 reading.

These are floors, not ceilings. More is welcome if it doesn't degrade the prose.

## Diversity seed (filled in per-novella)

You will receive **one** instantiation of this block in your specific brief:

```
- Setting tilt:   <a setting in one phrase>
- Tone tilt:      <a tone in one word>
- Form tilt:      <a narrative form in one phrase>
- Forbidden:      <one or two defaults to avoid>
```

Treat these as **starting tilts, not constraints**. Depart from them if the story demands. The forbidden defaults are non-negotiable: do not write the listed defaults. Examples (illustrative — the actual cohort uses different combinations):

| Seed slot | Example values |
|---|---|
| Setting | "generation ship mid-voyage", "coastal hospital over one winter", "monastery archive", "1970s research station in the Antarctic", "small-town courthouse over a long trial" |
| Tone | "comic", "elegiac", "procedural", "uncanny", "documentary" |
| Form | "epistolary", "first-person retrospective", "third-person rotating POV across 4 characters", "second-person", "framed narrative (story-within-a-story)" |
| Forbidden | "no coming-of-age framing", "no quest narrative", "no romance as primary thread", "no detective/mystery resolution", "no apocalyptic setup" |

## Contamination guards

The eval relies on the novella being absent from pretraining. Your novella **must**:

- Use **original character names** for all named entities. Do not name characters after real historical figures, public-domain literary characters, mythological figures, or well-known fictional characters. Original-sounding *common* names (Jane, Peter) are fine; specific identifiable names (Hermione Granger, Holden Caulfield, Hamlet) are not.
- Use **original settings**. Do not set the novella in real, specific, identifiable locations (London, Tokyo, Hogwarts, Middle-earth). Fictional places named in original ways are fine ("Maren's Bay", "the Carbiniere Quarter"). Real *types* of place (a coastal town, a hospital, a ship) are fine.
- Avoid **direct allusion** to recognisable works. References to general literary, mythological, or scientific concepts are fine; near-quotation or unmistakable pastiche is not.
- Do not reference real public figures by name. Fictional analogues are fine.
- Do not include passages that read as if lifted from a known work. If a sentence feels stylistically derivative, rewrite it.

## Originality vs. familiarity, in one line

The reader should feel they are reading something new. They should not feel they are reading something *strange* — write coherent, well-paced prose. Originality is at the level of names, settings, and specifics, not at the level of style.

## Style and craft floor

- Coherent narrative across all 10 chapters.
- Each chapter readable as a unit but contributing to the whole.
- Prose at the level of a competent literary-fiction novella. Not experimental beyond the form-tilt seed.
- Internal consistency: facts established in earlier chapters are not contradicted later (unless the contradiction is intentional and explained — e.g., an unreliable-narrator form-tilt).

## What you do not need to do

- You do not need to write questions about the novella — that is a separate step done by a different model.
- You do not need to anticipate how the SUT will be quizzed — focus on planting the structural elements above. Question construction is downstream.
- You do not need to write a summary or analysis of the novella. The memory-targets doc is structured; do not narrate it.
- You do not need to explain your authorial choices in either file.

## Hand-off

Deliver `novella.md` and `memory-targets.md` as two separate files in a directory named for the novella (e.g., `cohort-1/novella-3/`). Provided the structural requirements and contamination guards are met, the novella is accepted into the cohort.

A reviewer pass will check structural requirements against `memory-targets.md` claims and spot-check the novella for contamination markers and consistency. Failed novellas can be revised by the same author model with feedback or replaced.

## Cross-references

- [`README.md`](../README.md) — project overview, eval philosophy.
- [`tasks.md`](./tasks.md) — Track 1 (book-episodic) structure that this asset serves.
- [`memory-targets-spec.md`](./memory-targets-spec.md) — companion-doc format.
- [`question-set-spec.md`](./question-set-spec.md) — downstream consumer of the novella + memory-targets.
- [`validity.md`](./validity.md) — the broader confound and contamination discussion.
- [`worked-example-book-track.md`](./worked-example-book-track.md) — what the run actually looks like with these assets in place.
