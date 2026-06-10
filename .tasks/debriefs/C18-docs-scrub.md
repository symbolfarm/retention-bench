# Debrief: C18 Docs scrub — narrow public docs to evergreen reference

**Completed:** 2026-06-10
**Commit:** 83c8dee

## What shipped

- **Archived two internal decision records** to `docs/archive/` (dev-only):
  `clbench-pivot-plan.md` (a "not-yet-locked" joint-scoping doc with a
  reuse/retire table, C-series roadmap, and open decisions D1–D3) and
  `clbench-task-triage.md` (the C1 decision record). Their public-worthy content
  — what retention-bench adds on top of CL-Bench — already lives in the root
  `README.md`.
- **Un-archived `trace-schema.md` + `task-definition-schema.md`** back to public
  `docs/`. They document the exact formats the public quickstart (`./run.sh
  smoke` → `python -m harness` + `python -m scorer`) produces and consumes, and
  `sut-interface.md` cross-references both. C16 had over-archived them, which
  would have left the public SUT-builder contract linking into nothing on `main`.
- **Scrubbed all four public docs** (`metrics`, `sut-interface`, `trace-schema`,
  `task-definition-schema`) of internal bookkeeping: bare task-IDs (M#/B#/C#),
  "decision #N" pointers to the now-archived `decisions-checklist.md`, the dead
  "CL-N" working name, `[[wikilinks]]`, and a stale "Turn 5 design-dialogue"
  note. Translated where a ref carried meaning, dropped where it was pure
  bookkeeping. Also refreshed a stale example `model_id` (anthropic → the current
  `deepseek/...`) in `trace-schema.md` for consistency with the live stack.
- **Repointed navigation:** rewrote `docs/README.md` index for the new four-doc
  set; updated the root README "Documentation" section (was "start here →
  pivot-plan"); fixed `TASKS.md`'s pivot-plan link and the pending `C8` task
  file's two triage links to the archive paths.
- **Verified** with `scripts/promote.sh dryrun`: `main`'s `docs/` = the four
  scrubbed docs + index (+ the deferred constructive brief, see below); archive
  excluded; leak check clean.

## Descoped / deferred

- **`constructive-sut-development-brief.md` left untouched** (per Toby). It has
  already been exported + edited into the separate constructive-retention
  project; its retention-bench copy will be tailored down to the external
  **integration contract** (Part A — requirements) in a later side-by-side, with
  the model-building guidance (Parts B–D) living with the builder. Until then it
  keeps its "Audience: An AI agent (Claude)" framing and still links to the
  now-archived `clbench-pivot-plan.md` / `clbench-task-triage.md` (Pointers
  table) — so it is the one public-bound doc with links that dangle on `main`.
  This is fine for now: C17 (the public cutover) is deferred indefinitely, and
  the brief will be tailored before any cutover. Not listed in the public index;
  flagged there as "in progress."
- Did not rewrite the *content* of the kept docs beyond jargon removal + link
  fixes (out of scope).

## Design decisions

- **Un-archiving reverses part of C16.** C16 classified `trace-schema` /
  `task-definition-schema` as "standalone-era" by keyword/date, but they document
  formats the headline quickstart still uses. Confirmed with Toby before moving.
- **`decisions-checklist.md` stays archived; "decision #N" pointers de-jargoned
  in place.** The checklist is genuine internal archaeology; the public docs
  already state each rule, so the pointers added nothing for an outside reader.
- **Translated the `N`-axis residue in `metrics.md`'s resource section to "across
  the run"** rather than mechanically to `k`. The section predates the N→k
  rename and "across `k`" would have been semantically wrong (k = resets-since-
  read, not session count); "across the run" sidesteps the stale terminology
  without a deeper content rewrite.

## Observations

- The real find wasn't task-IDs — it was that the *kept* public docs weren't
  self-contained on `main`. `sut-interface.md` leaned on five archived specs
  (`trace-schema`, `task-definition-schema`, `decisions-checklist`, `protocol`,
  `interface`), and only `metrics.md` had been de-linked (by C16). A "kept
  public" verdict needs a link-closure check, not just a per-file content pass.
- **The deeper open question surfaced and was deliberately deferred:** the repo
  straddles two paths — the legacy book-track harness (`./run.sh smoke`, the
  README's headline) which the pivot plan marks *for retirement*, and the
  CL-Bench extension (`gain_curve` / `SubprocessSystem`) which is the pivot's
  contribution and the path the constructive transformer SUT actually runs on.
  "Which is the public story?" determines which docs are even public long-term.
  That belongs to the constructive-retention planning, not a docs scrub.

## Follow-ups

### Filed as tasks

- None filed yet. The constructive integration-contract carve-down and the
  book-track-vs-CL-Bench public-story decision are both live items but are folded
  into the upcoming constructive-retention planning rather than filed blind.

### Considered and dropped

- *Move the constructive brief to archive to keep it off `main`* — rejected:
  Toby wants it tailored (not archived), and C17 is deferred, so leaving it in
  `docs/` on `dev` is safe until the carve-down.
