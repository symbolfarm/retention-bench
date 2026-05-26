# Debrief: B3 LLM-as-judge scorer

**Completed:** 2026-05-26
**Commit:** (see commit log)

## What shipped

`scorer/protocols.py` — `Scorer` protocol + `ExactMatchScorer` implementation
+ `get_scorer()` dispatcher keyed by `question_type` and `scorer_mode`.  Two
modes: `"exact-match"` (default, M6-identical) and `"judge"` (routes
`entity_tracking` / `multi_hop` to the LLM judge).  Unknown types raise
`ValueError` immediately (hard error, no silent fallback).

`scorer/judge.py` — `JudgeScorer` implementation.  Uses Anthropic SDK tool-use
(`judge_verdict` tool) for schema-validated `{score, rationale}` output — no
fragile `json.loads`.  Reason-then-score prompt structure.  Temperature 0.
Model read from `RETENTION_BENCH_JUDGE_MODEL` env var, defaulting to
`claude-sonnet-4-6`.  Matches the SUT call-site idiom (`anthropic.Anthropic(api_key=...)`).

`scorer/aggregate.py` — `aggregate_records()` gains a `scorer_mode` kwarg
(default `"exact-match"`).  Per-record output gains `scorer_kind`; judge-scored
records gain `judge_rationale`.

`scorer/__main__.py` — `--scorer {exact-match,judge}` flag.  When `--scorer judge`,
writes judge rationales to a sibling `scoring.jsonl` keyed by `record_id`.

`tests/fake_anthropic_shim/anthropic.py` — extended to support `tool_use`
fixture entries (alongside the existing text-response format), enabling
deterministic judge tests.

`tests/fixtures/fake_judge_responses.yaml` — canned tool-use responses for the
q3-flip smoke scenario (3 judge calls: prior=0, ceiling=1, retention=1).

`tests/test_scorer_judge.py` — 16 new deterministic offline tests covering:
dispatch logic, ExactMatchScorer unit, M6 backward-compat regression
(`--scorer exact-match` keeps q3 excluded), q3-flip under `--scorer judge`
(entity_tracking false-negative now contributes to curve), `scoring.jsonl`
written and keyed by `record_id`, q4 surface_factual stays exact-match
regardless of mode, mixed-type run.

`docs/metrics.md` — "Scorer integration (B3)" section added, covering scorer
seam, dispatch table, output fields, judge implementation shape, and backward
compatibility.  **Partially addresses B7** — see follow-ups below.

Full test suite: **58 passed, 1 skipped** (the 1 skipped was pre-existing).

## Descoped / deferred

- Multi-judge / ensemble scoring — explicitly out of scope.
- Human calibration / annotation pipeline.
- `judge_resource_appendix.jsonl` write-out — the architecture is documented
  in `metrics.md` and the `--scorer judge` path writes `scoring.jsonl`, but
  per-call token counts for the judge are not yet accumulated into a separate
  appendix file.  The `JudgeScorer.score()` return value doesn't surface token
  usage; adding it is a small follow-up.
- Re-running historical runs with the judge — opt-in per run, as scoped.

## Design decisions

**DELIBERATE DEVIATION from decision #6 (library preference):** Decision #6
recommended using DeepEval `GEval` or Inspect AI's scorer catalogue rather than
a hand-rolled judge.  This task implements a **hand-rolled judge** instead.
Rationale (to be mirrored into the decisions-checklist):

> Our custom harness already owns orchestration, the P/C/R(k) curve, and the
> probe contract.  An eval framework (DeepEval/Inspect) would contribute only
> its judge-prompt scaffold (~5% of the value) while imposing its full
> dependency weight and its own event-loop assumptions.  The scorer seam
> (`Scorer` protocol in `scorer/protocols.py`) keeps a future `DeepEvalScorer`
> adapter slot open without any changes to the harness or curve renderer — so
> if DeepEval's metric battery becomes valuable later, it plugs in as a third
> implementation.

**Scorer seam design:** `Scorer` is a structural protocol (`typing.Protocol`),
not an ABC.  `get_scorer()` returns the appropriate instance based on
`question_type` and `scorer_mode`.  The judge singleton is lazily instantiated
on first judge-mode call (deferred API key check) and resettable via
`reset_judge_singleton()` for test isolation.

**Tool-use for structured output:** `JudgeScorer` uses `tool_choice={"type":
"any"}` with a single `judge_verdict` tool.  This forces the model to output
structured `{score, rationale}` rather than free-text JSON, eliminating the
parse-failure class of bugs that plagued early judge implementations.

**surface_factual always bypasses judge:** Even with `--scorer judge`, the
dispatch returns `ExactMatchScorer` for `surface_factual`.  This is locked per
the B3 design decisions.

## Observations

**q4 gold-answer quality issue (flagged, not fixed):** q4 ("What sound does
the narrator imagine hearing?", gold: `"a heartbeat"`) is `surface_factual` —
so exact-match applies in both modes.  The SUT answered `"The old man's
heartbeat"`, which exact-match scores 0, and by the locked dispatch this
question stays excluded under `--scorer judge` too.  The gold answer `"a
heartbeat"` is too terse to serve as a reliable scoring target: any natural
answer like "The old man's heartbeat" or "a loud heartbeat" will be excluded.
This is a **question-authoring / gold-answer quality issue**, not a scorer bug.
Flagged as a candidate follow-up task.

**Four hardcoded Anthropic call sites:** with `JudgeScorer`, there are now 4
places in the codebase that instantiate `anthropic.Anthropic(api_key=...)`:
`no_state`, `notes_llm`, `naive_rag`, and now `scorer/judge.py`.  Task B9
("LLM backend abstraction") was already scoped to unify these; the judge is
now an explicit argument for B9's scope growth.

## Follow-ups

### Filed as tasks

None filed from this debrief (parent serializes the task file updates).

### Drive-by cleanup landed

None.

### Considered and dropped

- **Accumulating judge token counts to `judge_resource_appendix.jsonl`** —
  `JudgeScorer.score()` currently discards `response.usage`.  Adding it would
  require plumbing the token counts back through `aggregate_records` or making
  `JudgeScorer` stateful.  Deferred: not load-bearing for the B3 acceptance
  criteria and the architecture is documented.
- **Soft scoring (0..1 float from judge)** — the tool schema uses
  `"enum": [0, 1]` so the judge returns binary.  Fractional scores could
  improve sensitivity for borderline cases but would require changes to
  `aggregate_records` to treat judge scores differently from exact-match scores
  (which are also binary today).  Deferred to a future task.
