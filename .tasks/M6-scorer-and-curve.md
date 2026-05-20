# M6 Exact-match scorer + retention-curve renderer

**Priority:** medium
**Blocked by:** M1
**Touches:** `scorer/`, `tests/`

## Context

The scorer is a pure function over the trace: it reads the per-`QUIZ` per-question records, scores each answer, computes `P(q)`, `C(q)`, `R(k, q)` per question, and aggregates into the normalised retention curve `(R−P)/(C−P)`. For MVP, exact-match is sufficient (decision #6A+C: per-question-type scorers, surface-facts use exact-match, LLM-judge for richer types comes later as B3).

Critical property: the scorer is **swappable** (decision #6, "The harness emits a per-`QUIZ` record file; scoring is a pure function over that file, swappable later"). Keep it cleanly separated from the harness — no shared state, no side effects on the trace, the scorer reads files and emits files.

## Goal

A Python module that consumes a trace from M2 and produces (a) per-question score records, (b) a `(P, C, R(k))` table per question, and (c) the aggregate normalised retention curve printed to stdout.

## Acceptance criteria

- [ ] `scorer/` package with at least: `exact_match.py`, `aggregate.py`, `curve.py`, `__main__.py`.
- [ ] Exact-match scorer: case-insensitive, whitespace-normalised string match between `sut_answer` and `gold`. Score = 1.0 or 0.0.
- [ ] Aggregate logic per `docs/metrics.md`:
  - Per-question: collect `P(q)`, `C(q)`, `R(k, q)` from probe-typed records.
  - Normalised retention: `(R(k,q) − P(q)) / max(C(q) − P(q), ε)` with documented ε (e.g. 0.05).
  - Questions where `C(q) ≈ P(q)` (within ε) are reported but excluded from aggregation, per the metrics.md rule.
- [ ] Curve renderer: prints a table like:
  ```
  question_id | P    | C    | R(1) | norm_R(1)
  q1         | 0.00 | 1.00 | 1.00 | 1.00
  q2         | 1.00 | 1.00 | 1.00 | (excluded — C≈P)
  ...
  aggregate (k=1, n_usable=3): 0.67
  ```
- [ ] `python -m scorer <run-dir>/trace.jsonl` is the entry point.
- [ ] Pytest coverage for:
  - Exact-match edge cases (case, whitespace, punctuation).
  - Aggregate excludes `C≈P` questions.
  - Normalised retention math on a hand-crafted record set.
- [ ] Scorer is a pure function: given the same trace input, produces byte-identical output. No state, no side effects.

## Relevant files

- `docs/trace-schema.md` (from M1) — the input contract.
- `docs/metrics.md` — the `(R−P)/(C−P)` formula, ε convention, aggregation rules.
- `docs/decisions-checklist.md` (#6, #10) — scoring approach, question-exposure-count.

## Decisions already made

- Exact-match only for MVP (#6A surface-facts component). LLM-judge for entity-tracking/multi-hop/thematic is B3, post-MVP.
- Scorer is swappable; live behind the per-`QUIZ` records file emitted by the harness (#6 closing paragraph).
- `question_seen_before` is an integer count per #10B; not load-bearing for exact-match scoring but should be preserved in score records for downstream analysis.

## Out of scope

- LLM-judge scoring (B3).
- Multi-SUT comparison or leaderboard rendering (post-MVP).
- Plot rendering (matplotlib/etc); printed table is sufficient for MVP.
- Per-question-type score weighting; aggregate is unweighted mean for now.

## Notes for the implementer

- The scorer reads the trace; it does NOT need to know about the harness, the SUT, or `DIR`. If you find yourself importing from `harness/`, you've crossed a line — the data contract is the trace file, period.
- "Excluded — C≈P" handling: report these in the per-question table so they're visible, but drop them from the aggregate. Don't fail-loud; smoke test will hit this with the public-domain text.
