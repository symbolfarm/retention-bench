# Debrief: B11 Wire judge token usage into judge_resource_appendix

**Completed:** 2026-05-27
**Commit:** fe0ca39

## What shipped

`JudgeScorer` now accumulates per-call token usage and writes a sibling
`judge_resource_appendix.jsonl` in judge mode:

- `JudgeScorer.__init__` initialises side-channel accumulators
  (`api_call_count`, `input_tokens`, `output_tokens`, `resolved_model_id`).
- `JudgeScorer.score()` calls `_accumulate_usage(response)` right after each
  API call (only on the path that actually hits the API — the
  `parsing_status != "ok"` early-return makes no call and accumulates nothing).
- `JudgeScorer.resource_appendix()` returns the aggregate dict
  (`kind:"api"`, `model_id`, `api_call_count`, `input_tokens`,
  `output_tokens`), mirroring the SUT `resource_appendix` conventions.
- `scorer.protocols.get_judge_appendix()` reads the accumulated appendix off
  the lazily-instantiated judge singleton (returns `None` if the judge was
  never engaged).
- `scorer/__main__.py` writes `judge_resource_appendix.jsonl` (single
  aggregate line) in judge mode, only when `get_judge_appendix()` is non-None.
- `docs/metrics.md` updated with the concrete appendix shape.
- Three new tests: accumulation totals match the fake fixture (380/145/3);
  no appendix in exact-match mode; no appendix when judge mode sees only
  `surface_factual` records.

## Descoped / deferred

- Multi-judge / ensemble accounting (already B3 out-of-scope).
- FLOPs / wall-clock for the judge — token + `api_call_count` is enough per
  the brief.

## Design decisions

- **Side-channel accumulation over a richer return type.** The brief offered
  three shapes (extend the return tuple, side-channel on `JudgeScorer`, or a
  result object). Chose the side-channel: `Scorer.score()` keeps its
  `(score, scorer_kind, rationale|None)` signature, so `ExactMatchScorer` and
  every existing caller stay untouched. The accumulator lives only where the
  spend originates.
- **Retrieval via `get_judge_appendix()` reading the module singleton.**
  `aggregate_records` doesn't hold a reference to the scorer instance, so the
  appendix is fetched after the run from the `protocols` singleton. Fresh per
  process (CLI = one run per process); `reset_judge_singleton()` already
  isolates tests.
- **`model_id` from `response.model`, not the requested model string.**
  Captures the resolved model id the API actually used; falls back to the
  configured model. Last-write-wins (constant across a temperature-0 run).
- **Write the appendix only when the judge is engaged.** No empty/zero file
  for exact-match mode or judge runs that contain only `surface_factual`
  records — the absence of the file means "no scoring spend", which is the
  honest audit signal.
- **Single aggregate JSONL record, not per-call lines.** The brief asked for
  accumulation; per-call provenance already lives in the scoring rationale
  path. One line keeps it a lean run-level budget number.

## Observations

- `scorer/__main__.py:21` and `docs/metrics.md` already *documented* the
  `judge_resource_appendix.jsonl` sibling before this task — B3 wrote the spec
  and left the wiring. B11 just closed the gap to match the existing docs.
- The fake-anthropic shim already exposed `usage.input_tokens/output_tokens`
  and `response.model`, so no shim changes were needed for offline tests.

## Follow-ups

### Filed as tasks

None.

### Considered and dropped

- Per-call usage lines in the appendix — dropped; the run-level aggregate is
  what the SUT-vs-scoring budget separation needs, and per-record rationale
  provenance is already in `scoring.jsonl`.
