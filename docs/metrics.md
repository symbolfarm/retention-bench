# Metrics

The headline output of a retention-bench evaluation is a **reset-axis retention curve**: normalised retention as a function of `k`, the number of hard `RESET`s the run executed. Each point applies a measured prior–ceiling band normalisation to the whole-run reward on a Continual Learning Bench task. This is the axis CL-Bench cannot express — its `mean_gain` is a single number at one implicit reset density. Resource metrics are reported alongside, not collapsed into the headline.

> **Status tags.** Metrics in this document are marked **[implemented]**
> (computed and rendered by the shipped code) or **[specified]** (defined here
> as part of the metric design, but not yet computed — nothing tagged
> [specified] appears in any current output). The curve itself, `W(m)`/`W_norm`,
> the bootstrap CIs, the `P`/`C` baselines, and the CL-Bench reconciliation are
> all [implemented]; the summary statistics and most resource *aggregations*
> are [specified] (their raw events are recorded).

## The reset-axis gain curve (the pivot's net-new axis)

`retention_bench.gain_curve.run_reset_sweep` runs three kinds of arm on one
CL-Bench task + system, each from a *fresh* survive-dir:

- **ceiling `C`** — `NoReset`, no wipe: state accumulates unbroken (`R(0)`).
- **prior `P`** — `EveryNInstances(1)` with `wipe_on_reset=True`: the survive-dir
  is cleared on every boundary, so each instance is seen by a fresh, stateless
  process. This is CL-Bench's stateless baseline in our hard-reset vocabulary.
- **points `R(k)`** — one stateful (non-wiping) arm per requested schedule; `k`
  is the *measured* `system.scheduled_resets`, not the nominal density.

The hard `RESET` is enforced, not requested: in subprocess mode the SUT is
launched in its own session/process group and the kill signals the whole group
(`SIGKILL` via `killpg`, also fired on a response timeout), so child processes
die with it; in container mode the same whole-tree semantics are enforced
independently by `docker rm -f`. Nothing survives a `RESET` except the on-disk
survive-dir.

> The uniform sweep above measures **graceful degradation** across repeated
> erasure. A different question — *did capability migrate into the durable
> artifact?* — needs the **phased store-removal** protocol (reset once at the
> train/probe boundary via `--reset-at`), because uniform resets wipe a SUT's
> store mid-learning and conflate "nothing migrated" with "no time to learn". See
> [`phased-store-removal.md`](phased-store-removal.md).

Each point is the band-normalised gain, reusing
`scorer.aggregate.normalised_retention`:

```
norm_gain(k) = (R(k) − P) / max(C − P, ε)
```

Interpretation: how much of what was *learnable in principle for this SUT* (the
gap `C − P`) survived `k` hard resets.

- Values near 1 — the SUT retained the learnable gap across the resets.
- Values near 0 — the SUT scored no better than its stateless prior after `k` resets.
- Negative values — post-reset performance below prior (the SUT got confused by its own surviving state).

The `ε` floor excludes the curve when the band collapses (`C ≈ P`): there is no
learnable signal to retain. Such runs are reported `EXCLUDED` and points show no
normalised value. (On the constructive SUT, whose output is gibberish by
construction, the band is ~0 and the curve *correctly* excludes — the honest
negative result, visible on the axis rather than asserted in prose.)

**`ε` is relative to the task's achievable range**: the absolute
threshold is `ε = 0.05 × r_max`, where `r_max` is CL-Bench's per-task maximum
run-mean reward (`scoring.band_epsilon`). A schedule that leaves some instances
structurally unscored compresses every run-mean by exactly `r_max` — on
`symbolic_associative_retention`'s default schedule (`r_max = 16/26 ≈ 0.615`) an
absolute 0.05 would silently demand ~8% of the *achievable* range while asking
5% of a fully-scored task. For binary rewards on a fully-scored schedule
(`r_max = 1`) this reduces to the historical "0.05 of the score range". The
`--epsilon` CLI flag remains an *absolute* override.

`k_max` is bounded by the run: a sweep that places `S` hard resets admits
`k ∈ {1, …, S}`.

> **`k` indexes reset *count*, not placement.** Two arms with equal measured `k`
> but different reset placement (`--reset-every 3` vs `--reset-at "10"`) are
> *different experiments* — the same `k` can wipe state mid-learning or after a
> train/probe boundary, with very different retention consequences. Compare
> points across systems only at matching schedules, and report the schedule
> alongside `k` (the curve carries each arm's `schedule_label` and measured
> `reset_ordinals` for exactly this reason).

### Post-reset-window reward `W(m)` — retained vs. relearned

Whole-run `R(k)` dilutes the signal it exists to measure: a run with one reset
at instance 30 of 90 scores 30 pre-reset instances identically to the ceiling
arm, so the reset's damage is averaged against instances it could not have
affected — curve sensitivity ends up depending on run length and reset
placement. Worse, a SUT that *relearns quickly* after a reset is
indistinguishable in `R(k)` from one that *retained*; separating those is
arguably the benchmark's actual question.

`W(m)` is the reward-side analogue of the cold-start *compute* metric below:
the mean per-instance reward over the first `m` instances after each hard
reset, pooled across the run's resets. Each window is truncated at the run end
and at the next reset (an instance completed at the next reset's ordinal is
still pre-that-reset, so it belongs to the current window; windows never
overlap). At `--reset-every 1` density every post-reset window truncates to a
single instance. Default `m = 3` (`--window-m`).

Alongside the raw `W(m)`, the curve reports the prior and ceiling arms' means
over the *same run ordinals* (valid because all three arms play the identical
instance sequence — the same precondition the CL-Bench reconciliation relies
on) and the window-band normalisation

```
W_norm = (W − P_w) / max(C_w − P_w, ε)
```

Matching ordinals cancels any structurally unscored instances that land inside
the window, so `W_norm` is directly comparable to `norm_gain(k)`.
Interpretation: **high `norm_gain` + high `W_norm` — retained. High `norm_gain`
+ low `W_norm` — relearned fast** (the state didn't survive; the SUT is
sample-efficient, which is interesting but is not retention). `W_norm` is
`None` for a no-reset arm and when the window band `C_w − P_w` is itself below
`ε`.

### Uncertainty: bootstrap CIs

Every arm is a single run of ~26–90 binary-reward instances, so a point's
reward resolution (`1/n ≈ 0.011–0.038`) is comparable to `ε` itself — a one-run
point on a narrow band can be noise. Each curve point therefore carries
**percentile-bootstrap confidence intervals** over the per-instance `outcomes`
(retained on every point for exactly this post-hoc use):

- `R(k)` CI: resample the point arm's per-instance rewards with replacement,
  recompute the mean; percentile interval over `B` replicates.
- `norm_gain` CI: resample **all three arms independently** per replicate and
  recompute `(R* − P*) / max(C* − P*, ε)` — prior/ceiling uncertainty
  propagates, so a band sitting near `ε` yields an honestly wide interval
  rather than a false-precise point. `P` and `C` also carry their own mean CIs.

Defaults: `B = 1000` (`--n-boot`; `0` disables), two-sided 95% (`--ci-level`),
deterministic under a fixed seed. Implementation:
`scoring.bootstrap_mean_ci` / `scoring.bootstrap_norm_gain_ci`. The bootstrap
resamples instances within one run — it quantifies within-run sampling noise,
not run-to-run variance; multiple seeds/runs per arm remain the gold standard
(see Reporting).

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

### Running it

Run it against any SUT speaking the `SubprocessSystem` contract (see
[`sut-interface.md`](sut-interface.md)):

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
> normalised value. The corpus + `--reset-at` machinery is in place; the
> non-monotonic *shape* needs a retaining-but-imperfect SUT plugged into the same
> command.

## Baselines reported alongside the curve

The curve is *normalised*, but the un-normalised arms are reported separately to
make the SUT legible:

- **Mean `P`** — how much the SUT scores cold (stateless, wiped every instance). A high `P` indicates contamination or general-knowledge inflation.
- **Mean `C`** — the SUT's capability ceiling on this task with state accumulating unbroken. A low `C` indicates the SUT can't do the task even with full retained state.
- **Mean `C − P`** — the learnable gap. If small, the task isn't measuring retention at this SUT, and the curve sits in a tiny band that must not be over-interpreted (and is `EXCLUDED` when `< ε`).

## Summary statistics

A curve is the primary artifact. Summary statistics are secondary and useful for ranking.

- **AURC (Area Under Retention Curve)** [specified]: integral of `norm_gain(k)` over `k ∈ [1, k_max]`. Higher is better. Easy to compare across SUTs for a fixed task.
- **Half-retention `k`** [specified]: the smallest `k` at which `norm_gain(k)` drops below 0.5 — "how many resets before this system falls apart." Lower is worse.
- **Mean `C − P`** [implemented]: the learnable gap, as above (the curve header's `band`). If small, the curve is reporting on a narrow band and should not be over-interpreted.
- **Degradation shape classifier (optional)** [specified]: categorise the curve as linear, stepped, cliff, or flat. Useful for qualitative comparison but not a scalar.

Summary statistics should always be reported with the curve, not instead of it.

## Background: the per-question band metric

The band normalisation above is inherited from the original **per-question**
`P`/`C`/`R(k)` probe formulation, which the retired book-track harness produced.
It is kept here as the *definition* of the band metric the reset-axis curve
reuses; it is **not** a live pipeline (the per-question scorer, its
`question_type` aggregation, and the `python -m scorer` CLI were retired with the book track —
only `scorer.aggregate.normalised_retention` and `EPSILON` survive). For a single
scored question `q` about reading material `m`:

- `P(q)` — score on a `prior` probe containing `q`, issued *before* reading `m`.
- `C(q)` — score on a `ceiling` probe, *after* reading `m` and *before* the next `RESET`, within the same SUT process.
- `R(k, q)` — score on a `retention` probe issued after `k ≥ 1` `RESET`s following the read of `m`.

with the identical normalisation, `normalised_retention(k, q) = (R(k,q) − P(q)) /
max(C(q) − P(q), ε)`. The reset-axis curve lifts this from per-question probes to
whole-run rewards on a CL-Bench task: `R`, `P`, `C` become run-mean rewards of
the three arms, and the `k` axis becomes the run's hard-reset density.

### Stenography vs. understanding (an interpretive lens)

When a per-question or per-`question_type` breakdown is available, the most
informative cut is by question type, because it separates *understanding
transfer* from *stenography*. Consider `notes_llm`, which retains by writing
cumulative notes to the survive-dir — externalised episodic memory, done
competently. A strong *pooled* curve may mean nothing more than "facts survived
in the notes." The discriminating question is whether retention **separates by
type**:

- **`surface_factual`** — answers a competent note-taker can carry verbatim. High retention here is expected and says little about comprehension.
- **`multi_hop`** / **`entity_tracking`** — require synthesis the notes do not literally contain. Retention here is the signal that *understanding*, not just text, survived the reset.

Interpretation rule: **separation** (strong `surface_factual`, collapsing
`multi_hop`) is the understanding-transfer signal the benchmark exists to
measure; **flat-high across all types** is a *warning*, not a triumph — it
suggests the task is rewarding stenography, or that the `multi_hop` questions
aren't actually requiring synthesis. (The CL-Bench-native reset-axis path scores
a single task reward per instance, so this per-type cut is a property of the
per-question formulation and a target for a future per-type reward task, not a
field the current `gain_curve` emits.)

## Scoring is owned by the CL-Bench task

retention-bench no longer ships its own scorers. On the live path, each instance's
reward is produced by the **CL-Bench task's own reward function** (e.g. the
interval-IoU scorer for `blind_spectrum_monitoring`); retention-bench consumes
those per-instance rewards as the `R`/`P`/`C` run means. The only scoring
primitive retention-bench owns is the band normalisation
(`scorer.aggregate.normalised_retention` + `EPSILON`) — the single shared home
for `(R − P) / max(C − P, ε)`, so every consumer normalises against one
definition.

The book-track `Scorer` seam (exact-match / LLM-as-judge dispatch by
`question_type`, the `judge_resource_appendix`, the `python -m scorer` CLI) was
retired with the per-question harness. It is preserved only in
`docs/archive/` on the `dev` branch for "why" archaeology (not part of the
public snapshot).

## Resource metrics

Resource metrics are reported per run and as aggregates across the run. They are not collapsed into the score; they live alongside it. `SubprocessSystem` records two kinds of CL-Bench `UsageEvent` tagged `call_type="compute"`: a per-response event carrying the SUT's self-reported `flops` / `tokens_in` / `tokens_out` / `model_id`, and a per-instance event carrying the survive-dir storage footprint.

### Token / compute usage

- **Tokens (and FLOPs) per response (in/out)** [implemented: recorded as per-response `UsageEvent`s]. From the SUT's reply `resource` self-report. Reveals how much each query costs.
- **Cumulative tokens / FLOPs across the run** [specified: the per-response events are recorded; no shipped aggregation]. Total cost of completing the run.
- **Cold-start cost** [specified: derivable from the recorded per-response events plus each arm's `reset_ordinals`; no shipped aggregation]: compute spent in the first responses of each post-reset session. A proxy for how much effort the SUT spends reconstructing working state from the survive-dir. A high cold-start cost is a legitimate architectural signal. (The *reward*-side analogue is the post-reset-window reward `W(m)` above, which **is** implemented.)
- **Cost per unit score** [specified]: cumulative tokens (or FLOPs) / task reward. A rough efficiency proxy.

### Survive-dir (filesystem) usage

The per-instance storage `UsageEvent` records `survive_dir_bytes`,
`survive_dir_delta_bytes`, and `survive_dir_file_count` (measured before any
bounce — the kill cannot change on-disk state).

- **Footprint at end of each instance** [implemented: recorded per instance]. Absolute measure of accumulated state — the bytes that must survive a hard reset.
- **Delta per instance** [implemented: recorded per instance]: bytes added/modified/removed. Reveals information rate and whether the system prunes.
- **Growth trajectory across the run** [specified: derivable from the recorded per-instance events; no shipped rendering]: does the survive-dir grow linearly with instances, sublinearly (compression), or is it bounded? A constructive SUT's footprint steps up on a growth event.
- **Storage efficiency** [specified]: task reward / survive-dir size. Loosely, "useful state per byte." Imperfect but informative.

Note: raw size is not the whole story. A 10 GB vector store with excellent retrieval may outperform a 10 MB markdown file with poor retrieval. Report all storage metrics and let the reader compare systems on their own efficiency frontier.

### Wall-clock time

- Per session and cumulative [specified: not currently recorded]. Realism check: a system that scores well but takes 100x longer is not necessarily practical.

## Reporting format

A retention-bench result for one SUT on one task should include (items built
from [specified] metrics — the summary statistics and resource *curves* —
apply once those are implemented; see the status tags above):

1. **The reset-axis retention curve** (`norm_gain(k)` vs `k`), with the per-point bootstrap CIs as error bars (§Uncertainty).
2. **The three arms** (mean `P`, mean `C`, mean `C − P`, each with its CI), the effective `ε` and task `r_max`, and the band-exclusion status.
3. **The post-reset-window reward** (`W(m)` and `W_norm` per point, with `m`) — the retained-vs-relearned discriminator.
4. **Summary statistics** (AURC, half-retention `k`).
5. **Resource curves** (tokens/FLOPs vs `k`, survive-dir size vs instance index, cold-start cost vs `k`).
6. **System-class declaration** (the manifest `mode` + hardware tier + relevant configuration).
7. **Reset schedule** (`--reset-every` / `--reset-at`, the *measured* `k` per arm, and the measured `reset_ordinals` — equal `k` at different placement is a different experiment).
8. **Seed count** and variance notes (the bootstrap covers within-run noise only; run-to-run variance needs repeated runs).
9. **CL-Bench reconciliation** (`clbench_mean_gain` per point) — required for replicability and cross-checking against CL-Bench's own gain.

Leaderboards, if they exist, should publish all of the above, not just a single score.

## Benchmark validity: prior saturation and material novelty

The `C ≈ P` exclusion (drop a curve when the learnable gap `C − P < ε`) is the
right call — a benchmark that returns *null* when there is no learnable signal is
trustworthy, not broken. But it has a consequence that must be tracked: it makes
the benchmark's **effective signal model-dependent**.

A band collapses precisely when the SUT's base model *already does the task at
prior* (`P ≈ C`). As base models improve, more tasks/instances saturate their
priors and the measurable band shrinks. This is not hypothetical: an early smoke
run excluded 4 of 5 questions because a capable base model already answered them
at prior.

The implication reframes the synthetic-data / task track:

- **Material novelty is a validity requirement, not a variety nice-to-have.** A renewable supply of material the model *provably has not seen* is what keeps `C − P` open and the benchmark able to measure anything at all. As models improve, only genuinely novel material keeps priors low enough to leave a learnable gap.
- **Target: keep mean `P` low** (well below `C`). Report mean `P` prominently (see "Baselines reported alongside the curve") and treat a rising mean `P` across cohorts as a signal that the task pool is aging out, not as SUT improvement.

This does **not** motivate removing the exclusion — the exclusion stays. It
motivates feeding the benchmark novel material fast enough that prior saturation
never starves the signal.

## What is deliberately not measured in v1

- **Failure-mode diagnostics** (was state not stored, stored but not retrieved, retrieved but misapplied, corrupted across resets?). Important for the benchmark's long-term diagnostic value but deferred to task-level design.
- **Transfer to novel tasks** post-reset. A lifelong-learning concern orthogonal to the retention question this benchmark measures; better served by separate benchmarks.
- **Weight-update catastrophic forgetting** as a first-class score. The constructive SUT class exercises weight updates, but quantifying forgetting is deferred to a future extension.
