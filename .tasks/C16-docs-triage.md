# C16 `docs/` triage + index

**Priority:** medium
**Blocked by:** C13
**Touches:** `docs/`, `docs/README.md` (new index), `docs/archive/` (new, dev-only)

## Context

`docs/` is a graveyard: ~15 standalone-era spec files (mostly dated 2026-05-16 to
-20), several self-labelled "v0.1 starting points, not stable", several now
**contradicting the CL-Bench pivot** ([[project_clbench_pivot]]). A public reader
can't tell current from dead.

Rough split to validate during the task (read each before deciding — don't go by
date alone):

- **Current / keep on `main`:** `clbench-pivot-plan.md`, `clbench-task-triage.md`,
  `metrics.md`, `sut-interface.md`, `constructive-sut-development-brief.md`.
- **Superseded standalone-era → dev-only archive:** `spec.md`, `protocol.md`,
  `interface.md`, `topology.md`, `validity.md`, `extensions.md`,
  `open-questions.md`, `tasks.md`, `book-spec.md`, `memory-targets-spec.md`,
  `worked-example-book-track.md`, `cohort-1-models.yaml`, `cohort-1-seeds.md`,
  `question-set-spec.md`, `task-definition-schema.md`, `trace-schema.md`,
  `decisions-checklist.md`.

Per C13, superseded docs are parked under a **dev-only `docs/archive/`** that the
`PUBLIC_PATHS` exclude keeps off `main` — retained for "why" archaeology on `dev`,
absent from the public tree.

## Goal

`docs/` on `dev` is split into a curated current set (lands on `main`) and a
dev-only `docs/archive/` of superseded material, fronted by a `docs/README.md`
index that orients a public reader.

## Acceptance criteria

- [ ] Each doc classified current-vs-superseded by **reading it**, not by date;
      flag any that are partly-current (extract the live part, archive the rest)
      rather than mis-binning.
- [ ] Superseded docs moved to `docs/archive/` (git-tracked on `dev`); C13's
      `PUBLIC_PATHS` exclude confirmed to keep `docs/archive/` off `main`.
- [ ] `docs/README.md` index: one line per current doc (what it covers), and a
      short note that pre-pivot specs live in `archive/` for history.
- [ ] No current doc left referencing a now-archived doc by a path that breaks on
      `main` — fix or relativize cross-links in the kept set.
- [ ] Dry-run promote (or re-run C13's) shows `main`'s `docs/` contains only the
      curated set + index.

## Relevant files

- All of `docs/` (read to classify).
- New: `docs/README.md`, `docs/archive/`.
- `PUBLIC_PATHS` (the `docs/archive/` exclude — coordinate with C13).

## Decisions already made

- Archive (retain on `dev`), don't delete — keeps "why" archaeology, matching how
  the project already treats superseded work (`superseded` in LOG, debriefs kept).
- Current set is the pivot-era docs; standalone-era specs are superseded.

## Out of scope

- Rewriting the *content* of the kept docs (only classification, moving, indexing,
  and fixing broken cross-links).
- README at repo root (C14).
