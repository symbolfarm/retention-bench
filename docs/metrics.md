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

### Per-`question_type` breakdown (stenography vs. understanding)

The pooled curve is also reported **broken down by `question_type`**, not just
aggregated across all questions. This is not cosmetic — it is the load-bearing
signal that distinguishes *understanding-transfer* from *stenography*.

Consider `notes_llm`, which retains by writing cumulative notes to `DIR` —
externalised episodic memory, done competently. If it posts a strong *pooled*
retention curve, that may mean nothing more than "facts survived in the notes."
The discriminating question is whether the curve **separates by type**:

- **`surface_factual`** — answers a competent note-taker can carry verbatim.
  High retention here is expected and says little about comprehension.
- **`multi_hop`** (and `entity_tracking`) — require synthesis the notes do not
  literally contain. Retention here is the signal that *understanding*, not just
  text, survived the reset.

**Interpretation rule:**

- **Separation** — strong `surface_factual`, collapsing `multi_hop` — is the
  understanding-transfer signal the benchmark exists to measure. A system that
  only stenographs will show exactly this gap.
- **Flat-high across all types** is a *warning*, not a triumph: it suggests the
  benchmark (or this asset's questions) is rewarding stenography, or that the
  `multi_hop` questions aren't actually requiring synthesis. Inspect the asset
  before celebrating the curve.

The scorer emits the per-type curve in `render_curve` (a `by question_type:`
block after the pooled aggregate), computed by
`scorer.aggregate.aggregate_curve_by_type`. The `C ≈ P` exclusion is applied
*within* each type group, so a type's `n_usable` can differ from the pooled `n`.

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

## Reset-axis curve on Continual Learning Bench (the pivot's net-new axis)

Everything above is the book-track formulation (per-question `P`/`C`/`R(k)`
probes inside one run). After the 2026-06-07 pivot (see
[`clbench-pivot-plan.md`](clbench-pivot-plan.md)), the same normalisation is
applied to **whole-run rewards on a Continual Learning Bench task**, where the
axis is the number of *hard resets* `k` the run executed. This is the thing
CL-Bench cannot express: its `mean_gain` is a single number at one implicit
reset density.

`retention_bench.gain_curve.run_reset_sweep` runs three kinds of arm on one
CL-Bench task + system, each from a *fresh* survive-dir:

- **ceiling `C`** — `NoReset`, no wipe: state accumulates unbroken (`R(0)`).
- **prior `P`** — `EveryNInstances(1)` with `wipe_on_reset=True`: the survive-dir
  is cleared on every boundary, so each instance is seen by a fresh, stateless
  process. This is CL-Bench's stateless baseline in our hard-reset vocabulary.
- **points `R(k)`** — one stateful (non-wiping) arm per requested schedule; `k`
  is the *measured* `system.scheduled_resets`, not the nominal density.

The per-point number is the **same** band normalisation as the book-track curve,
reusing `scorer.aggregate.normalised_retention`:

```
norm_gain(k) = (R(k) − P) / max(C − P, ε)
```

The `C ≈ P` exclusion carries over unchanged: when the band collapses the curve
is reported `EXCLUDED` and points show no normalised value. (On the constructive
SUT, whose output is gibberish by construction, the band is ~0 and the curve
*correctly* excludes — the honest negative result for the constructive SUT,
now visible on the axis rather than asserted in prose.)

### Reconciliation with CL-Bench's gain

We contribute the axis, **not** a competing formula. CL-Bench's normalised gain
is `(r_sf − r_sl) / (r_max − r_sl)`; under `r_sf → R(k)`, `r_sl → P`,
`r_max → C` that is exactly `norm_gain(k)`. The non-tautological check is on the
numerator: our `R(k) − P` (a difference of run-mean rewards) must equal
CL-Bench's `mean_gain`, which its own `build_benchmark_aggregate` computes as the
mean of *per-instance* `rollout_reward − baseline_reward` matched by
`instance_id`. The two agree exactly because both arms play the identical
instance set, so the mean of the per-instance differences equals the difference
of the means. Each `GainCurvePoint` carries `clbench_mean_gain` straight from
their function, and `tests/test_gain_curve.py::test_reconciles_with_clbench_mean_gain`
asserts the equality on every point — i.e. at the matching `k`, our number is
CL-Bench's gain on the same run.

Run it against any SUT speaking the `SubprocessSystem` contract:

```bash
python -m retention_bench.gain_curve --task blind_spectrum_monitoring \
  --task-kwarg variant=five_ch_wide --task-kwarg num_instances=6 \
  --sut "python -m constructive.clbench_main" \
  --extra-pythonpath suts/constructive --reset-every 1 --reset-every 2
```

### Placing resets on a concept-drift boundary (the non-monotonic story)

`--reset-every N` spaces resets uniformly. The richer claim the pivot wants to
expose is **non-monotonic**: usually more resets means less retention, but a
single reset placed *on* a concept-drift boundary can *help* by clearing a
now-stale prior. To test that you must place resets deliberately, not uniformly —
that is `ExplicitBoundaries`, exposed on the CLI as `--reset-at`:

```bash
# BSM `default` schedule: 3 stages × 30 instances, drift at ordinals 30 and 60.
# On-drift {30,60} vs just-after {35,65}, k matched at 2 resets each.
python -m retention_bench.gain_curve --task blind_spectrum_monitoring \
  --task-kwarg schedule=default --task-kwarg probe_mode=true \
  --sut "python -m constructive.clbench_main" \
  --extra-pythonpath suts/constructive \
  --reset-at "30,60" --reset-at "35,65" --name constructive-drift
```

The `default` three-stage schedule (`Wideband → +Narrowband → Full grid`) is a
concept drift: new radio channels switch on at each stage boundary, so belief
the system accumulated about "empty" guard bands becomes a confidently-wrong
prior the instant the next stage starts. A reset *on* the boundary (`{30,60}`)
discards exactly that stale prior; a reset *just after* (`{35,65}`) instead
discards the fresh, correct adaptation the system has already begun — same `k`,
opposite effect. `ExplicitBoundaries` ordinals are 1-based completed-instance
counts; ordinals past the run length never fire.

**Data prerequisite.** The `default` schedule declares
`corpus_id: mixed_grid_lifecycle`, so CL-Bench requires that frozen corpus on
disk (it refuses to silently fall back to seeded scans, raising
`FileNotFoundError`). The corpus ships git-tracked inside the cl-benchmark
dependency at `data/blind_spectrum_monitoring/mixed_grid_lifecycle.{jsonl,_metadata.json}`
— a fresh clone already has it. It is byte-deterministic (seeded `SpectrumDGP`
rollouts, seeds 42/43/44); `retention_bench.bsm_corpus` regenerates or verifies
it:

```bash
python -m retention_bench.bsm_corpus --verify   # regenerate in a temp dir, compare sha256; writes nothing
python -m retention_bench.bsm_corpus            # (re)write into the cl-bench data dir if missing
```

> **Note on what's observable today.** With the current constructive SUT (output
> is gibberish by construction — out of scope to fix) the reward band collapses
> (`C ≈ P`), so the drift sweep renders `EXCLUDED` and every placement reports no
> normalised value. The corpus + `--reset-at` machinery is what C10 delivers; the
> non-monotonic *shape* needs a retaining-but-imperfect SUT plugged into the same
> command.

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

1. **The retention curve** (normalised retention vs. `k`), with error bars —
   pooled **and broken down by `question_type`** (see "Per-`question_type`
   breakdown"), so the stenography-vs-understanding separation is legible.
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
- `JudgeScorer` — LLM-as-judge via the OpenAI-compatible chat-completions API's
  tool-calling (`openai` SDK pointed at a configurable `base_url`). Returns a
  `{score, rationale}` verdict without free-text parsing.

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
  `moonshotai/kimi-k2.6` (a pinned frontier *open* model). Calls go to an
  OpenAI-compatible `base_url` (`RETENTION_BENCH_BASE_URL`, default OpenRouter)
  via the `openai` SDK and require `OPENROUTER_API_KEY`. (B9, 2026-06-03, moved
  the judge and all SUT call sites off the Anthropic SDK to this provider-neutral
  shape.) Judge-quality validation of the pinned open model is tracked in B14.
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
  {"kind": "api", "model_id": "moonshotai/kimi-k2.6", "api_call_count": 3, "input_tokens": 380, "output_tokens": 145}
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

## Benchmark validity: prior saturation and material novelty (B15)

The `C ≈ P` exclusion (drop a question when the learnable gap `C − P < ε`) is
the right call — a benchmark that returns *null* on a question with no learnable
signal is trustworthy, not broken. But it has a consequence that must be
tracked: it makes the benchmark's **effective `n` model-dependent**.

A question is excluded precisely when the SUT's base model *already knows the
answer cold* (`P ≈ C`). As base models improve, more world-knowledge questions
saturate their priors and fall out the bottom of the aggregate. This is not
hypothetical: the B9 smoke run excluded 4 of 5 questions (`n_usable = 1`)
because a capable base model already answered them at prior.

The implication reframes the synthetic-data track:

- **Material novelty is a validity requirement, not a variety nice-to-have.** A
  renewable supply of material the model *provably has not seen* is what keeps
  `C − P` open and the benchmark able to measure anything at all. As models
  improve, only genuinely novel material keeps priors low enough to leave a
  learnable gap. This raises the priority of the synth-gen work in
  [[tasks]] (cohort dispatch / B8) and the mock-transcript / in-context-leaderboard
  work (B5) from "variety" to "load-bearing for validity."
- **Target: keep mean `P` low** (well below `C`) on the questions that drive the
  curve. Report mean `P` prominently (see "Baselines reported alongside the
  curve") and treat a rising mean `P` across cohorts as a signal that the asset
  pool is aging out, not as SUT improvement.

This does **not** motivate removing the exclusion — the exclusion stays. It
motivates feeding the benchmark novel material fast enough that prior saturation
never starves the aggregate.

## What is deliberately not measured in v1

- **Failure-mode diagnostics** (was memory not stored, stored but not retrieved, retrieved but misapplied, corrupted across clears?). This is important for the benchmark's long-term diagnostic value but is deferred to task-level question design in v2.
- **Transfer to novel tasks** post-clear. This is a lifelong-learning concern orthogonal to the CL-N retention question and is better served by separate benchmarks.
- **Weight-update catastrophic forgetting.** Deferred to a future extension.
