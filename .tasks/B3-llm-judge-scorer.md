# B3 LLM-as-judge scorer integration

**Priority:** medium-high (raised by today's notes-llm live run —
exact-match scorer excluded 2/5 questions where notes-llm answered
correctly in substance; this is the next bottleneck on producing
trustworthy retention curves).
**Blocked by:** nothing
**Touches:** `scorer/`, `tests/test_scorer_*.py`,
`docs/metrics.md` (post-scoping), possibly `pyproject.toml`
(new dependency).

## Context

The MVP scorer is exact-match (M6). It's correct but brittle: today's
live run of notes-llm against the Tell-Tale Heart smoke task produced
substance-correct answers like "Three police officers" (gold: "the
police") and "The old man's heartbeat" (gold: "a heartbeat") that
exact-match scored 0, excluding them via the C≈P rule. This wastes
real retention signal.

Per decision #6 (recommendation A via C): **surface-fact questions
should bypass LLM judgment to avoid wasting variance budget; thematic /
open-ended questions need multi-judge.** Library reuse preferred over
hand-rolled judge logic — DeepEval `GEval` and Inspect both ship
suitable scorer catalogues. Confirmed 2026-05-17: custom harness for
the protocol; existing library for per-question scoring.

The harness emits a per-`QUIZ` records file (`questions.jsonl`):
`(question, probe, k, sut_answer, gold, type)`. Scoring is a pure
function over that file — the M6 exact-match scorer already proves
this design. The judge integration is "swap in a different scorer
function for some question types."

## Goal

A scorer that handles surface-fact questions with exact-match (cheap,
deterministic) and thematic / open-ended questions with an LLM judge
(preferably reusing DeepEval `GEval` or Inspect). Output format
unchanged from M6 — same retention curve shape — but per-question
records gain a `scorer_kind` field and judge runs gain a
`judge_rationale` field for auditability.

## Acceptance criteria

- [ ] Scorer dispatch by `question_type`: surface_factual → existing
      exact-match; thematic / open-ended → LLM judge.
- [ ] Judge produces a 0/1 (or 0..1) score per question with a
      brief textual rationale.
- [ ] Rationales persisted to a sibling JSONL file (e.g.
      `scoring.jsonl`) keyed by `record_id` — keep `questions.jsonl`
      lean and the rationale auditable.
- [ ] Same `P`, `C`, `R(k)` aggregation: judge-scored questions
      flow into the same retention curve as exact-match questions
      without special casing in the renderer.
- [ ] On rerun against the M7 smoke output, the previously-excluded
      questions (q3 "the police", q4 "a heartbeat" if their types
      warrant judge scoring) now contribute to the curve.
- [ ] Fake-mode judge for tests: deterministic stub or
      record/replay so the test suite doesn't depend on a live API.
- [ ] All existing tests pass; new tests cover the dispatch logic
      and the judge-rationale persistence.

## Open questions to scope with Toby

1. **Library choice: DeepEval `GEval` vs Inspect vs hand-rolled.**
   Recommended direction (decision #6): library. Comparative
   trade-offs to evaluate at scoping:
   - DeepEval `GEval` — popular, prompt-template-driven, easy to
     plug in. Pulls in `deepeval` (heavier dep with own opinions).
   - Inspect (Anthropic-Internal? or UK AISI's `inspect_ai`) —
     research-grade, more flexible, also heavy.
   - Hand-rolled — minimal dep, full control, but reinventing.
   Decision shapes everything downstream.

2. **Judge model.** Same model as the SUT? Same model as the
   benchmark "house" (e.g. always Sonnet)? Bigger model than the SUT
   (e.g. Opus to judge Haiku/Sonnet SUTs)? Affects cost, bias, and
   leaderboard fairness.

3. **Per-question-type dispatch matrix.** `surface_factual` →
   exact-match is clear. `thematic` → judge. What about other
   types we'll add? Decide whether new types default to judge or
   to a hard error until explicitly mapped.

4. **Judge calibration.** How do we know the judge agrees with
   humans? A small held-out set with Toby-graded gold labels would
   bootstrap confidence. In scope or future task?

5. **Stochasticity.** Judges are LLMs and non-deterministic at
   non-zero temperature. Multi-judge (e.g. 3 judges, majority vote)
   is the standard mitigation. Single-judge for MVP or multi from
   the start?

6. **Cost accounting.** Judge calls cost real money per scoring
   run. Should the judge's tokens flow into the same
   `resource_appendix` as the SUT's? Or a separate
   `judge_resource_appendix`? (Probably separate — different
   concerns; SUT budget vs scoring budget.)

7. **Backward compatibility.** Today's M6 scorer is the only one;
   B3 either replaces it (with a `--scorer exact-match` opt-out)
   or supplements it (`--scorer judge` opt-in, exact-match
   default). Migration path matters for reproducibility of past
   smoke runs.

## Relevant files

- `scorer/` — current exact-match implementation; scoring is
  already a pure function over `questions.jsonl`.
- `tests/test_scorer_exact_match.py`, `tests/test_scorer_aggregate.py`,
  `tests/test_scorer_cli.py` — coverage to preserve.
- `docs/metrics.md` — needs a write-in for judge integration once
  shape is decided (currently has a TODO from M6 era; see TASKS.md
  backlog item B7).
- `tasks/smoke-test/sample-output*.md` — useful test corpus: real
  notes-llm run showed exactly the kind of false-negatives this
  task fixes.
- `runs/smoke-test-2026-05-25T12-51-56Z-34ca7c/questions.jsonl` —
  the actual records that prompted this prioritisation; could be
  the first calibration set.

## Out of scope

- Multi-judge / ensemble scoring beyond a single-judge baseline
  (revisit if single-judge variance is too high; explicitly noted
  as a possible follow-up).
- Human calibration UI / annotation pipeline. We'll grade a small
  set by hand if needed.
- Per-question rubrics beyond what `GEval`-style criteria require.
- Re-running every historical run with the new scorer to back-fill
  curves — opt-in per run is sufficient.
- Naive-RAG SUT (B2), Docker packaging (B4), LLM-backend
  abstraction (B9) — separate tasks.
