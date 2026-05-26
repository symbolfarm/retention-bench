# B11 Wire judge token usage into judge_resource_appendix

**Priority:** medium
**Blocked by:** nothing (B3 landed)
**Touches:** `scorer/judge.py`, `scorer/protocols.py`, `scorer/aggregate.py`,
`scorer/__main__.py`, `tests/test_scorer_judge.py`, `docs/metrics.md`

## Context

B3 shipped the LLM-as-judge scorer with the *architecture* for separate judge
cost accounting documented in `docs/metrics.md`, but the wiring is incomplete:
`JudgeScorer.score()` discards `response.usage`, so judge token counts never
reach a `judge_resource_appendix`. This was acceptable for B3 (resource
accounting was decision-#6 open-question territory, not a hard acceptance
criterion) but should be closed before judge runs are used to report real
numbers — the whole point of a *separate* judge appendix is that scoring spend
must not contaminate the SUT's budget.

The non-trivial part is interface shape: the `Scorer` protocol currently
returns `(score, scorer_kind, rationale|None)`. Threading usage out needs a
decision — extend the return tuple, accumulate into a resettable side-channel
on `JudgeScorer`, or return a richer result object. Pick one; keep
`ExactMatchScorer` (no usage) clean under whatever shape is chosen.

## Goal

Judge LLM token usage (input/output tokens, api_call_count, model_id) is
accumulated across a scoring run and written to a `judge_resource_appendix`
artifact, distinct from the SUT's `resource_appendix`.

## Acceptance criteria

- [ ] `JudgeScorer` captures `response.usage` per judge call.
- [ ] Usage accumulated across the run and written to a
      `judge_resource_appendix` (file or run-manifest field — match the
      shape `docs/metrics.md` already describes).
- [ ] `Scorer` protocol change (if any) keeps `ExactMatchScorer` clean.
- [ ] Tests assert accumulation with the fake judge (deterministic, offline).
- [ ] All existing tests pass.

## Relevant files

- `scorer/judge.py` — where `response.usage` is currently dropped.
- `scorer/protocols.py` — the `Scorer` return shape.
- `scorer/aggregate.py`, `scorer/__main__.py` — run-level accumulation + output.
- `docs/metrics.md` — already documents the intended appendix shape.

## Decisions already made

- Judge cost is a *separate* appendix from the SUT's (decision #6 open-Q6:
  different budgets — SUT budget vs scoring budget).

## Out of scope

- Multi-judge / ensemble accounting (B3 out-of-scope; revisit later).
- FLOPs/wall-clock for the judge — token + api_call_count is enough here.
