# C18 Docs scrub — narrow the public docs/ set to evergreen reference

**Priority:** medium
**Blocked by:** nothing
**Touches:** `docs/`, `docs/archive/`, `docs/README.md`, `README.md`, `TASKS.md`, `.tasks/C8-multistep-sut-adapter.md`

## Context

C16 triaged `docs/` current-vs-superseded but not public-vs-internal, and
left internal-flavoured content on the public side. Two of the five docs C16
"kept" read as internal decision records rather than public reference, and all
of them carry bare internal task-IDs (M1, B16, C9…) that mean nothing to an
outside reader.

This is release-credibility polish. C17 (the public-`main` cutover) is deferred
indefinitely, so nothing ships from this — but the public docs/ set should be
honest reference material before that flip ever happens.

Reviewed with Toby 2026-06-10:
- `clbench-pivot-plan.md` is a **joint-scoping decision record** ("not yet
  locked", reuse/retire table, C-series roadmap, open decisions D1–D3 addressed
  to Toby). Its only public-worthy content — what retention-bench adds on top of
  CL-Bench — is already in the root `README.md`. → **archive.**
- `clbench-task-triage.md` is the C1 decision record. → **archive.**
- `constructive-sut-development-brief.md` has already been exported + edited into
  the separate constructive-retention project. Its retention-bench copy will
  eventually become the external-facing **integration contract** (Part A only;
  builder guidance Parts B–D live with the builder), but that carve-down waits on
  a side-by-side with the exported version. → **deferred, untouched here.**

After this, the public docs/ set is `metrics.md` + `sut-interface.md` + the
index, with `README.md` as the landing page.

## Goal

Narrow the public docs/ surface to the two evergreen reference docs (the metric
and the SUT contract), archive the two internal decision records, and remove the
bare internal task-IDs from what stays public — so no outside reader trips over
project-internal bookkeeping.

## Acceptance criteria

- [ ] `clbench-pivot-plan.md` and `clbench-task-triage.md` moved to `docs/archive/`.
- [ ] Bare task-IDs (M#/B#/C#) in `metrics.md` and `sut-interface.md` translated
      to plain language or dropped — no `M1`/`B16`/`C9`-style refs remain in the
      two public docs.
- [ ] `docs/README.md` index lists only the public set (metrics + sut-interface),
      with the history/archive note intact.
- [ ] Root `README.md` "Documentation" section no longer points "start here →
      pivot-plan"; points at the actual public docs.
- [ ] No dangling links: `metrics.md`'s pivot-plan link, `TASKS.md:17`, and the
      pending `C8` task file's triage links updated to the archive path.
- [ ] `scripts/promote.sh dryrun` (or equivalent) shows `main`'s docs/ = metrics
      + sut-interface + index, archive excluded, leak check clean.

## Relevant files

- `docs/metrics.md`, `docs/sut-interface.md` (scrub + relink)
- `docs/clbench-pivot-plan.md`, `docs/clbench-task-triage.md` (archive)
- `docs/README.md`, `README.md`, `TASKS.md`, `.tasks/C8-multistep-sut-adapter.md` (relink)
- `PUBLIC_PATHS`, `scripts/promote.sh` (verification)

## Decisions already made

- Archive both pivot-plan and task-triage (internal decision records; not public
  reference). The public pitch already lives in `README.md`.
- Defer `constructive-sut-development-brief.md` to a later side-by-side; it
  becomes the external integration contract, not archived.
- Translate task-IDs rather than blindly delete: where a ref carries meaning
  ("the reset axis added in C4"), restate it in plain language; where it's pure
  bookkeeping, drop it.

## Out of scope

- Rewriting the *content* of `metrics.md` / `sut-interface.md` beyond task-ID
  removal and link fixes.
- The constructive integration-contract carve-down (own follow-up, with the
  side-by-side).
- Rewriting historical `.tasks/debriefs/*` — they accurately record their moment.
