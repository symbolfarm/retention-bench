# Metrics

> **Note (Turn 5, 2026-05-13):** This document is being updated in step with Turn 5 of [[design-dialogue]]. The atomic-event model and three-probe baselines (`prior` / `ceiling` / `retention`) reshape how the retention curve is computed: per-question normalisation against a measured prior–ceiling band, rather than against a single CL-0 baseline. The `N` axis is replaced by `k` (resets-since-relevant-read).

The headline output of a CL-N evaluation is a **retention curve**: normalised retention score as a function of `k`, the number of `RESET`s separating a `READ` event from the subsequent `retention`-probe `QUIZ`. Resource metrics are reported alongside, not collapsed into the headline.

## Per-question probes

For each scored question `q` about reading material `m`:

- `P(q)` — score on a `prior` `QUIZ` containing `q`, issued *before* `READ(m)`.
- `C(q)` — score on a `ceiling` `QUIZ` containing `q`, issued *after* `READ(m)` and *before* the next `RESET`, within the same SUT process.
- `R(k, q)` — score on a `retention` `QUIZ` containing `q`, issued after `k ≥ 1` `RESET`s following `READ(m)`.

A given run can produce `P` and `C` once each per question, and `R(k)` at multiple values of `k`. Multiple seeds / trials estimate variance at each (`q`, `k`).

## Normalised retention

The per-question normalised retention is:

```
normalised_retention(k, q) = (R(k, q) − P(q)) / max(C(q) − P(q), ε)
```

Interpretation: how much of what was *learnable in principle for this SUT* (the gap `C − P`) survived `k` `RESET`s. By construction:

- Values near 1 indicate the SUT retained the learnable gap.
- Values near 0 indicate the SUT scored no better than its prior-knowledge baseline after `k` resets.
- Negative values indicate post-reset performance below prior — possible if the SUT got confused by its own state.

The `ε` floor (typical `ε = 0.05` of the score range) excludes questions where `C ≈ P` (no learnable signal at this SUT) from aggregation. Such questions are reported separately as informative-but-not-aggregated.

## Retention curve

For a given SUT and task, the curve plots aggregated normalised retention vs. `k`:

- Aggregate `normalised_retention(k, q)` across questions `q` for each `k`. Default: mean, weighted by question-class (with thematic and retroactively-relevant questions weighted higher per [[tasks]]).
- Plot vs. `k = 1, 2, ..., k_max`.
- Curve shape is the primary artifact; summary statistics are derived from it.

`k_max` is task-dependent and bounded by the run's event sequence. A task with `S` `RESET` events admits `k ∈ {1, ..., S}` for material delivered before the first `RESET`.

## Baselines reported alongside the curve

The curve is *normalised*, but the un-normalised probes are reported separately to make the SUT legible:

- **Mean `P` across questions** — how much the SUT could answer cold. A high `P` indicates contamination or general-knowledge inflation.
- **Mean `C` across questions** — the SUT's capability ceiling on this asset. A low `C` indicates the SUT can't answer the questions even with the text fresh.
- **Mean `C − P`** — the learnable gap. If this is small, the asset isn't measuring memory at this SUT.

These three numbers contextualise the retention curve and prevent over-interpretation of a clean curve that sits in a tiny `C − P` band.

## Summary statistics

A curve is the primary artifact. Summary statistics are secondary and useful for ranking.

- **AURC (Area Under Retention Curve):** integral of normalised retention over `k ∈ [1, k_max]`. Higher is better. Easy to compare across SUTs for a fixed task.
- **Half-retention `k`:** the smallest `k` at which normalised retention drops below 0.5. A notion of "how many resets before this system falls apart." Lower is worse.
- **Mean `C − P`:** the learnable gap, as above. If small, the curve is reporting on a narrow band and should not be over-interpreted.
- **Degradation shape classifier (optional):** categorise the curve as linear, stepped, cliff, or flat. Useful for qualitative comparison but not a scalar.

Summary statistics should always be reported with the curve, not instead of it.

## Resource metrics

Resource metrics are reported per run and as aggregates across `N`. They are not collapsed into the score; they live alongside it.

### Token usage

- **Tokens per session (in/out).** Reveals how much a session costs.
- **Cumulative tokens across the run.** Reveals total cost of completing the task at this `N`.
- **Cold-start tokens:** tokens spent in the first `X%` of each post-clear session. A proxy for how much effort the SUT spends reconstructing working state from the filesystem. A high cold-start cost is a legitimate architectural signal.
- **Tokens per unit score:** cumulative tokens / task score. A rough efficiency proxy.

### Filesystem usage

- **Filesystem size at end of each session.** Absolute measure of accumulated state.
- **Delta per session:** bytes added/modified/removed. Reveals information rate and whether the system prunes.
- **Growth trajectory across `N`:** does filesystem size grow linearly with sessions, sublinearly (compression), or is it bounded?
- **Storage efficiency:** task score / filesystem size. Loosely, how much "useful state per byte." Imperfect but informative.

Note: raw size is not the whole story. A 10 GB vector store with excellent retrieval may outperform a 10 MB markdown file with poor retrieval. Report all storage metrics and let the reader compare systems on their own efficiency frontier.

### Access patterns (optional but encouraged)

- Files read per session, particularly per post-clear session.
- Files written per session.
- Re-access patterns: is the same file read many times, or does the SUT cache in working memory?

These reveal whether a memory system has genuine indexing or is scanning.

### Wall-clock time

- Per session and cumulative. Realism check: a system that scores well but takes 100x longer is not necessarily practical.

## Reporting format

A CL-N result for one SUT on one task should include:

1. **The retention curve** (normalised retention vs. `k`), with error bars.
2. **Summary statistics** (mean `P`, mean `C`, mean `C − P`, AURC, half-retention `k`).
3. **Resource curves** (tokens vs. `k`, filesystem size vs. event index, cold-start cost vs. `k`).
4. **Mode declaration** (pure LLM / notes / full harness, plus any relevant configuration).
5. **Awareness declaration** (clear-aware or clear-blind).
6. **Seed count** and variance notes.
7. **Per-question probe table** (raw `P`, `C`, `R(k)` values) — required for replicability and for post-hoc reanalysis under different aggregation choices.

Leaderboards, if they exist, should publish all of the above, not just a single score.

## Scorer integration (B3)

### Scorer seam

The scorer exposes a small `Scorer` protocol (defined in `scorer/protocols.py`):

```
score(record: dict) -> (score: float, scorer_kind: str, rationale: str | None)
```

Two implementations ship:

- `ExactMatchScorer` — case-insensitive, whitespace-normalised exact match.
  Never calls an API. Default for all question types under `--scorer exact-match`.
- `JudgeScorer` — LLM-as-judge via the Anthropic SDK's tool-use / structured
  output. Returns a `{score, rationale}` verdict without free-text parsing.

A future `DeepEvalScorer` (or other framework adapter) slots in as a third
implementation against the same protocol, without touching the harness or
curve renderer.

### Dispatch rules

Dispatch is keyed by `question_type` in the `questions.jsonl` record:

| `question_type`     | Default (`--scorer exact-match`) | `--scorer judge`  |
|---------------------|----------------------------------|-------------------|
| `surface_factual`   | exact-match                      | exact-match       |
| `entity_tracking`   | exact-match                      | judge             |
| `multi_hop`         | exact-match                      | judge             |
| unknown / unmapped  | hard error (fail loud)           | hard error        |

`surface_factual` bypasses the judge in all modes by design — these
questions are amenable to exact-match and routing them through a judge
wastes variance budget. Unknown types raise `ValueError` immediately (no
silent fallback), forcing the type to be explicitly assigned to a scorer
before it can be used.

### Output fields

Per-record output gains:

- `scorer_kind` — `"exact_match"` or `"judge"`.  Always present.
- `judge_rationale` — the judge's brief reasoning.  Present only for
  judge-scored records; absent for exact-match records (keeps
  `questions.jsonl` lean).

Judge rationales are persisted to a sibling `scoring.jsonl` file in the
run directory, keyed by `record_id`.  This keeps `questions.jsonl`
machine-readable and lean while making rationales auditable.

### Judge implementation

- Model: read from `RETENTION_BENCH_JUDGE_MODEL` env var; falls back to
  `claude-sonnet-4-6`.  Same idiom as the SUT implementations — a future
  task (B9) replaces all hardcoded Anthropic call sites uniformly.
- Prompt: reason-then-score structure.  The model produces a brief
  rationale before the verdict, which improves reliability on borderline
  cases.  Verdict is extracted via a tool call (`judge_verdict`), so no
  fragile free-text JSON parsing.
- Temperature: 0.  Single judge; multi-judge / ensemble is out of scope
  (revisit if single-judge variance is too high).
- Cost accounting: judge token usage is separate from SUT token usage.
  Judge costs appear in a sibling `judge_resource_appendix.jsonl` (distinct
  from the SUT's `resource_appendix`), written only when the judge is
  actually engaged (judge mode with ≥1 judge-eligible record). It is a
  single aggregate record (one JSONL line) accumulated across the run,
  mirroring the SUT `resource_appendix` conventions plus judge totals:

  ```json
  {"kind": "api", "model_id": "claude-sonnet-4-6", "api_call_count": 3, "input_tokens": 380, "output_tokens": 145}
  ```

  Per decision #6 (open-Q6): the SUT budget and the scoring budget are
  different, so judge spend must never roll into the SUT's appendix.

### Backward compatibility

`--scorer exact-match` (default) reproduces M6 behavior exactly — past smoke
runs re-score identically under the default.  The judge is strictly opt-in
via `--scorer judge`.

**Note:** this section partially addresses backlog B7 (metrics documentation
of scorer integration shape).  B7 is not fully closed — it also covers
multi-question-type weighting and the full reporting format update.

## What is deliberately not measured in v1

- **Failure-mode diagnostics** (was memory not stored, stored but not retrieved, retrieved but misapplied, corrupted across clears?). This is important for the benchmark's long-term diagnostic value but is deferred to task-level question design in v2. See [`extensions.md`](./extensions.md).
- **Transfer to novel tasks** post-clear. This is a lifelong-learning concern orthogonal to the CL-N retention question and is better served by separate benchmarks.
- **Weight-update catastrophic forgetting.** Deferred to [`extensions.md`](./extensions.md).
