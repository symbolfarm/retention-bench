# Debrief: C21 Reconcile sut-interface.md + metrics.md to the SubprocessSystem contract

**Completed:** 2026-06-11
**Commit:** 2e977ab

## What shipped

Rewrote the two public docs that were authored for the retired book-track so
they describe the live CL-Bench-native path, plus the index that points at them.

- **`docs/sut-interface.md`** — replaced the `READ`/`QUIZ`/`STAGE_INPUT`/
  `answers` event spine with the `SubprocessSystem` one-line-JSON query/reply
  per CL-Bench instance: request
  `{prompt, instance_id, instance_index, response_schema, feedback}` → reply
  `{action: {<fields matching response_schema>}, resource?}` (with the
  whole-reply-is-the-action convenience). Documented the `resource` self-report
  keys (`flops`/`tokens_in`/`tokens_out`/`model_id` lifted onto a compute
  `UsageEvent`; everything else preserved under `sut_resource`). Rewrote the
  worked example to a `bsm_accumulator` round-trip. Retained launch (subprocess
  / `ContainerLaunch`), DooD path translation, survive-dir, and hard-`RESET`
  mechanics — accurate already — but reframed them around `SubprocessSystem` as
  the primary path rather than as an addendum to the book-track loop.
- **`docs/metrics.md`** — promoted the reset-axis gain curve to the lead/primary
  formulation; demoted the per-question `P`/`C`/`R(k)` text to a "Background: the
  per-question band metric" section that defines the band normalisation the
  reset-axis curve reuses. Replaced the entire retired "Scorer integration"
  section (exact-match/judge dispatch, `python -m scorer` CLI, judge appendix —
  all deleted by C20) with a short "Scoring is owned by the CL-Bench task"
  section; folded the stenography-vs-understanding `question_type` content into a
  clearly-labelled interpretive lens (no longer claims a live `aggregate_curve_by_type`
  / `render_curve` emits it). Updated "Reporting format" and "Resource metrics"
  to the live `UsageEvent` channels (per-response compute + per-instance storage).
- **`docs/README.md`** — index blurbs for both docs rewritten; the
  constructive-SUT note's "valid `in-context` SUT" reworded to "first-class SUT".
- Removed the C20 "tracked separately / see the C20 debrief" notes from both docs.

Docs-only, no code touched. `scripts/promote.sh dryrun` clean (exit 0, no
dev-only leaks).

## Descoped / deferred

Nothing from the brief was descoped. The brief scoped P/C/R(k) + band metric;
the work also addressed the retired `Scorer` section because the goal said
"nothing reads as a live book-track pipeline" and that section described deleted
code (exact-match/judge/scorer CLI) as live — the single biggest book-track-as-
live problem in `metrics.md`. Folding that in was in-scope under the goal.

## Design decisions

- **`agentic | in-context` two-leaderboard split: retired.** The brief left its
  fate to the implementer ("CL-Bench's own leaderboard may subsume it"). Decided
  to drop the split entirely: CL-Bench owns the leaderboard, retention-bench
  contributes the reset-density `k` axis over the same systems. `mode` is recast
  from a leaderboard *router* to a free-form descriptive **system-class** label.
  Driver: the live manifests already violated the old enum (`bsm_accumulator`
  ships `mode: "notes"`), so the enum was already dead in practice.
- **Documented that the live harness does *not* read `sut-manifest.json`.** The
  `gain_curve`/`SubprocessSystem` path takes the launch command directly (`--sut`
  / `command`); nothing parses the manifest on the live path (confirmed by grep —
  only `harness/sut_process.py`, the book-track loader, references it). So the
  doc now frames the manifest as a packaging/declaration artifact and names
  `clbench_entrypoint` as the live launch field, with `entrypoint` demoted to
  "legacy book-track, kept for history."
- **Container launch documented as programmatic-only.** The `gain_curve` CLI is
  subprocess-only (`make_system` never passes `container=`); `ContainerLaunch` is
  reachable only via the API. Said so explicitly rather than implying the CLI can
  containerise.
- **`mode` example uses `bsm_accumulator` (`notes`)** as the canonical manifest,
  not `no_state` (deleted) — it's keyless, backs the smoke, and is the cleanest
  hard-reset illustration.

## Observations

- The kept manifests carry **both** `entrypoint` (book-track, sometimes `null`)
  and `clbench_entrypoint` (live). Only the latter matters today; a future
  cleanup could drop `entrypoint` from the manifests entirely once nothing
  references the book-track loader (it's already retired). Not filed — low value,
  and the field is harmless documentation of history.
- `tests/test_scorer_aggregate.py`'s module docstring still mentions
  `aggregate_curve_by_type` / `QuestionAggregate` (retired), though its actual
  imports are only `EPSILON, normalised_retention`. Stale comment in test code,
  out of scope for a docs task; noting it here rather than touching test files.
- `scorer/__pycache__/` still holds stale `.pyc` for the deleted modules
  (`curve`, `exact_match`, `judge`, `protocols`, `__main__`). Cosmetic; git-
  ignored; left alone.

## Follow-ups

### Considered and dropped

- *Strip the legacy `entrypoint` field from the three kept manifests* — code/asset
  change, out of this docs task's scope, and the field is harmless history. Not
  worth a task on its own; fold into any future manifest-schema touch.
- *Fix the stale `test_scorer_aggregate.py` docstring* — a one-line comment in a
  passing test; drive-by-able next time that file is opened, not worth a commit now.
