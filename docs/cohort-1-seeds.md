---
title: Cohort 1 — diversity seeds for first-cohort novellas
project: continual-learning-eval
status: seed set (Turn 6 of [[design-dialogue]], 2026-05-13)
authoring: Claude (proposed); awaiting Toby sign-off before dispatch
tags: [seeds, cohort-1, book-track]
---

# Cohort 1 — diversity seeds

Four seed-triples drafted to span different narrative architectures, not just different genres. Each is intended for one author model in the first cohort. Pair each seed with [`book-spec.md`](./book-spec.md) when dispatching.

The seeds target three independent axes:

- **Setting** chooses the world the model is working inside (constrains entity arcs, surface-fact texture).
- **Tone** chooses the register (constrains prose style, atmosphere).
- **Form** chooses the narrative architecture (POV, structure, temporal frame — the deepest diversity lever).
- **Forbidden** explicitly pushes off the default each model would otherwise drift toward.

The four below are pairwise distinct on all four slots.

## Seed 1 — Hospital procedural

```
Setting tilt:   coastal hospital over one winter
Tone tilt:      procedural
Form tilt:      third-person rotating POV across 4 staff
Forbidden:      no coming-of-age framing; no romance as the primary thread
```

Notes:
- Hospital affords natural entity arcs (patients moving through wards, staff across shifts) and surface-fact density (chart numbers, medication names, room layouts).
- Procedural register pairs cleanly with clinical detail without becoming sterile.
- Rotating POV gives natural multi-hop opportunities (one staff member sees the start, another sees the middle).

## Seed 2 — Generation ship, epistolary

```
Setting tilt:   generation ship mid-voyage, three centuries from arrival
Tone tilt:      uncanny
Form tilt:      epistolary (letters and log-entries between two characters in different ship sections)
Forbidden:      no quest narrative; no apocalyptic setup
```

Notes:
- Epistolary form makes retroactively-relevant facts natural: an offhand remark in an early letter becomes load-bearing when a later letter cues it. The form is also one of the strongest defences against model-default narrative architecture.
- Forbidding apocalyptic and quest framings pushes the author toward the slower, stranger possibilities of generation-ship fiction (rituals, institutional drift, intra-ship politics).
- "Uncanny" rather than "dark" or "tense" — atmosphere of wrongness without overt threat.

## Seed 3 — Monastery archive, retrospective

```
Setting tilt:   monastery archive over one liturgical year
Tone tilt:      elegiac
Form tilt:      first-person retrospective by an aged archivist
Forbidden:      no detective or mystery resolution; no romance as the primary thread
```

Notes:
- Liturgical year gives a clean 10-section structure that doesn't read as artificial chapters.
- First-person retrospective is the trickiest form for the eval — narrators can flag "and this would matter later" too overtly, breaking the retro-fact camouflage requirement. The brief's camouflage note guards against this; the question-author's validity check (#7) catches what gets through.
- Elegiac register diverges sharply from the procedural and the comic; gives the cohort tonal range.

## Seed 4 — Courtroom, comic, framed

```
Setting tilt:   small-town courthouse over a long civil trial
Tone tilt:      comic
Form tilt:      framed narrative (a former courtroom stenographer recounts the trial decades later)
Forbidden:      no quest narrative; no apocalyptic setup
```

Notes:
- A long civil (not criminal) trial keeps the comic register viable.
- Framed narrative — the outer frame is the elderly stenographer, the inner frame is the trial itself — gives a structural depth axis other forms don't have, and naturally affords retroactively-relevant facts (the stenographer's commentary draws together details the trial-as-experienced left ambiguous).
- Comic tone is the rarest in literary-fiction defaults; including it is the highest-diversity bet.

## Pairwise distinctness check

| Slot | Seed 1 | Seed 2 | Seed 3 | Seed 4 |
|---|---|---|---|---|
| Setting domain | medical | SF / shipboard | religious / archival | legal / civic |
| Setting temporal frame | one winter | mid-voyage (decades) | one year (cyclic) | one trial (then decades hence) |
| Tone | procedural | uncanny | elegiac | comic |
| Form (POV) | rotating 3rd | epistolary | 1st retrospective | framed (1st-of-1st) |
| Forbidden — primary | coming-of-age | quest | detective | quest |
| Forbidden — secondary | romance-as-primary | apocalyptic | romance-as-primary | apocalyptic |

All four are pairwise distinct on at least three of six slots. The two "no quest" seeds (2 and 4) are otherwise maximally different.

## What to dispatch per author model

Bundle (one author model receives):
- `book-spec.md` (with the per-novella diversity-seed block filled in from one row above).
- Light cover note: "Produce `novella.md` and `memory-targets.md` per the brief. Do not produce a question set."

The question-author model receives only `novella.md` and `memory-targets.md` from each completed novella.

## Pending Toby

- Sign-off on the four seeds (or substitutions).
- Choice of which author model gets which seed (or: random assignment, recorded for cross-asset analysis).
- Choice of question-author model (held constant across all four novellas — e.g., a single strong model — so the question-set generator is not itself a confound).
