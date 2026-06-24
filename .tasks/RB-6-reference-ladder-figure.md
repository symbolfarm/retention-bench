# RB-6 Reference-ladder figure + SUT-list update — the pre-C17 validity artifact

**Priority:** high
**Blocked by:** RB-4, RB-5
**Depends-on (external):** none
**Touches:** `README.md`, `run.sh`, `docs/**`, `scripts/**`

## Context

With [[RB-4]] (no-state floor) and [[RB-5]] (bounded-memory partial) landed, the
reference set finally spans a full *retention ladder*:

```
no_state  →  bounded_memory  →  associative_memory / bsm_accumulator  →  notes_llm  →  constructive
 (floor)      (partial)            (full, keyless)                       (LLM)        (research)
```

This task turns that into the artifact that makes the C17 public release
defensible: a committed, **reproducible-without-an-API-key** figure whose
retention curves visibly separate floor / partial / full on one task
(`symbolic_associative_retention`). A benchmark whose headline metric has never
been shown to discriminate retention is a reviewer's first attack; this closes
that. Curated in-loop (not fully delegated) because figure framing is a
judgment call.

## Goal

A committed gain-curve figure (and the script that regenerates it) showing
`no_state`, `bounded_memory`, and `associative_memory` on
`symbolic_associative_retention` across a reset sweep, with the three tiers
clearly separated; plus README/`run.sh` updated to list the full reference SUT
set and point at the figure.

## Acceptance criteria

- [ ] A regeneration script (e.g. `scripts/reference_ladder.sh` or a small
      Python driver) runs the three keyless SUTs through `gain_curve` offline and
      emits the curve data + figure deterministically.
- [ ] Figure committed (and/or the numeric P/C/R(k) table) showing tier
      separation; floor ≈ prior for k≥1, partial between, full on top.
- [ ] `README.md` reference-SUT list updated to include `no_state` +
      `bounded_memory` and reference the ladder figure.
- [ ] `run.sh` help/comment reflects the available keyless SUTs (today it only
      mentions `bsm_accumulator`).
- [ ] Fully offline / keyless; `scripts/promote.sh dryrun` clean.
- [ ] Full suite green: `.venv/bin/python -m pytest`.

## Relevant files

- `suts/no_state/`, `suts/bounded_memory/`, `suts/associative_memory/`
- `retention_bench/gain_curve.py`, `scorer/aggregate.py`
- `run.sh`, `README.md`, `scripts/promote.sh`, `PUBLIC_PATHS`

## Decisions already made

- **Three keyless tiers on one task** (`symbolic_associative_retention`) for the
  figure — LLM (`notes_llm`) and research (`constructive`) SUTs are named in the
  ladder narrative but kept out of the offline figure so it reproduces without
  credentials or torch surprises.
- **Curated in-loop**, not delegated to a subagent.

## Out of scope

- Cutting the orphan public `main` branch — that's C17; this is its input, not
  the cutover itself.
- naive_rag / store-removed probe (belongs with the episodic-memory work).
