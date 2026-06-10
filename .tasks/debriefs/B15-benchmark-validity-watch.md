# Debrief: B15 Benchmark validity — prior-saturation & question-type separation

**Completed:** 2026-06-03
**Commit:** 46d6872

## What shipped

Made per-`question_type` retention a first-class reported quantity and
documented the prior-saturation validity argument.

- `scorer/aggregate.py`: `QuestionAggregate` now carries `question_type`
  (captured first-seen when the aggregate is created). New
  `aggregate_curve_by_type()` buckets questions by type and reuses
  `aggregate_curve` within each group, so the per-`k` normalisation and `C ≈ P`
  exclusion are identical to the pooled path — just scoped per type.
- `scorer/curve.py`: `render_curve` appends a `by question_type:` block after
  the pooled aggregate. Deterministic (types and `k` sorted).
- `docs/metrics.md`: (1) "Per-`question_type` breakdown" subsection with the
  stenography-vs-understanding interpretation rule (separation = the signal we
  want; flat-high = stenography smell); (2) new "Benchmark validity: prior
  saturation and material novelty" section reframing synth-gen (B5/B8) material
  novelty from "variety" to load-bearing for validity, with a keep-mean-`P`-low
  target; (3) reporting-format checklist item 1 now calls for pooled **and**
  per-type curves.
- Tests: `test_curve_by_type_separates_question_types` (pooled hides 0.5,
  per-type exposes 1.0 vs 0.0), `test_curve_by_type_excludes_within_group`,
  `test_question_type_captured_on_aggregate`, plus a CLI assertion that the
  `by question_type:` block renders. 49 scorer tests green.

## Descoped / deferred

- No new CLI flag or machine-readable per-type output file. The breakdown rides
  the existing stdout render; a structured (JSON) per-type emission can come
  with the broader reporting-format work (B7) if a consumer needs it. The
  acceptance criteria asked for the curve to be *reported* broken down by type
  — stdout satisfies that at the current MVP fidelity.
- AURC / half-retention summary stats are not computed per type (they aren't
  computed pooled either yet — they live in the metrics doc as future
  summary-stat work). Per-type curves are the unit the brief asked for.

## Design decisions

- **Reuse `aggregate_curve` per group rather than re-implementing.** Guarantees
  the per-type curve uses byte-identical exclusion/normalisation logic to the
  pooled curve — no risk of the two drifting. Cost: questions are grouped into
  sub-dicts first (O(n) extra), negligible at benchmark sizes.
- **`question_type` first-seen wins on the aggregate.** It's constant per
  question across probes, so the first record that creates the aggregate sets
  it. Mirrors the existing "keep the first prior/ceiling" defensiveness.
- **Missing/blank `question_type` buckets under `"unknown"`** in the breakdown
  (rather than erroring). The scorer *dispatch* still fails loud on unknown
  types via `get_scorer`; the reporting layer is deliberately lenient so a
  render never crashes on a malformed record.
- **Interpretation rule lives in `docs/metrics.md`, not the renderer.** The
  render carries a one-line code comment pointer; the narrative + warning rule
  belong in the metrics doc where reviewers read them.

## Observations

- **Pre-existing env gap, not caused by B15:** `tests/test_*_fake_openai.py` (3
  tests) fail in this dev container with `FileNotFoundError: 'python'` — the
  harness spawns SUT subprocesses as `python`, but only `python3` /
  `.venv/bin/python` exist on PATH here. Confirmed by re-running with B15
  changes stashed (identical failure). Unrelated to the scorer; logged to the
  dev-env follow-up batch.
- `docs/metrics.md` "Scorer integration (B3)" section is **stale post-B9**: it
  still describes the judge as Anthropic-SDK / `claude-sonnet-4-6` (lines ~124,
  163-165, and the appendix `model_id` example). B9 moved the judge to the
  OpenAI-compatible SDK with a kimi judge. Out of B15 scope; flagged below.
- B15 was filed `low` priority and bundled a docs item with a code item; it
  fit comfortably in one session without a split.

## Follow-ups

### Filed as tasks

None.

### Considered and dropped

- Per-type AURC/half-retention summary stats — dropped; summary stats aren't
  computed pooled yet either, so this belongs to the broader summary-stat work,
  not B15.

### Worth filing (flagged for Toby, not yet filed)

- **docs/metrics.md B3/judge section is stale post-B9** (Anthropic SDK /
  `claude-sonnet-4-6` → OpenAI-compatible SDK / kimi). Small doc-accuracy fix;
  related to the B7 metrics rewrite and the B14 judge work. Left unfiled
  pending a steer on whether to fold into B7/B14 or file standalone.
