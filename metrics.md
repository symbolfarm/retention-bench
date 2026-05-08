# Metrics

The headline output of a CL-N evaluation is a **retention curve**: task score as a function of `N`. Resource metrics are reported alongside, not collapsed into the headline.

## Retention curve

For a given SUT and task:

- Run the task at `N ∈ {0, 1, 2, ..., N_max}`.
- At each `N`, run multiple seeds / trials to estimate variance (stochastic LLMs; see [`open-questions.md`](./open-questions.md) on determinism).
- Record task score at each `N`.
- The curve plots score vs. `N`.

`N_max` is task-dependent. For a task with `S` stages and between-stage-only clears, `N_max = S - 1`. For tasks allowing mid-stage clears, `N_max` can be larger and is specified per task.

## Summary statistics

A curve is the primary artifact. Summary statistics are secondary and useful for ranking.

- **AURC (Area Under Retention Curve):** normalised integral of score over `N`. Higher is better. Easy to compare across SUTs for a fixed task.
- **Half-retention `N`:** the smallest `N` at which score drops below 50% of the CL-0 score. A notion of "how many clears before this system falls apart." Lower is worse.
- **CL-0 score:** the baseline itself, reported separately. If this is low, the curve tells you less. Always report alongside derived statistics.
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

1. **The retention curve** (score vs. `N`), with error bars.
2. **Summary statistics** (CL-0 score, AURC, half-retention `N`).
3. **Resource curves** (tokens vs. `N`, filesystem size vs. `N`, cold-start cost vs. `N`).
4. **Mode declaration** (pure LLM / notes / full harness, plus any relevant configuration).
5. **Awareness declaration** (clear-aware or clear-blind).
6. **Seed count** and variance notes.

Leaderboards, if they exist, should publish all of the above, not just a single score.

## What is deliberately not measured in v1

- **Failure-mode diagnostics** (was memory not stored, stored but not retrieved, retrieved but misapplied, corrupted across clears?). This is important for the benchmark's long-term diagnostic value but is deferred to task-level question design in v2. See [`extensions.md`](./extensions.md).
- **Transfer to novel tasks** post-clear. This is a lifelong-learning concern orthogonal to the CL-N retention question and is better served by separate benchmarks.
- **Weight-update catastrophic forgetting.** Deferred to [`extensions.md`](./extensions.md).
