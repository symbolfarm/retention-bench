# Documentation

retention-bench extends [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)
(Asawa et al.) with a hard **RESET** (a process-kill discontinuity across which
only an on-disk survive-directory persists) and a **constructive/parametric**
system class. It is a research *instrument* — a workbench we use and share, not a
benchmark seeking submissions; there is no leaderboard. These docs are the
reference for building a system-under-test (SUT) and interpreting its results;
the project overview, thesis, and quickstart are in the
[root README](../README.md), and the research agenda is in
[`ROADMAP.md`](ROADMAP.md).

| Doc | What it covers |
|---|---|
| [`ROADMAP.md`](ROADMAP.md) | The research agenda, published ahead of the measurements: the storage-vs-memory thesis, why the hard RESET, the probe ladder (recall → composition → aggregation → revision → application), confidence tiers, and the open questions. Start here for *why*. |
| [`sut-interface.md`](sut-interface.md) | The system-under-test process contract — the `SubprocessSystem` one-line-JSON query/reply per CL-Bench instance, the survive-dir / hard-`RESET` mechanics, resource self-report, and launch (subprocess / container). Start here if you're building a SUT. |
| [`metrics.md`](metrics.md) | The retention metric — the reset-axis gain curve `norm_gain(k) = (R − P) / max(C − P, ε)`, the `C ≈ P` exclusion rule, and reconciliation with CL-Bench's gain. |
| [`associative-curriculum.md`](associative-curriculum.md) | Implementation spec for the first small constructive-retention curriculum task: deterministic symbolic associations, exact scoring, memorization-vs-transfer probes, the probe-space width / chance level, the never-bridged held-out composition split, and the repeated-exposure extension path. |
| [`related-work-studybench.md`](related-work-studybench.md) | How Retention Bench relates to StudyBench / "Machine Studying" (Li, Battle & Khattab, 2026): the shared understanding-vs-memorization thesis, the orthogonal reset-axis vs inference-compute-axis measurement, paradigm/SUT mapping, and leverage opportunities. |
| [`constructive-sut-development-brief.md`](constructive-sut-development-brief.md) | Development guidance for constructive (train-and-grow) SUTs: what the harness guarantees, what a constructive system must own, and the curve shapes to aim for. |
| [`reference-ladder.md`](reference-ladder.md) | The reference-SUT ladder: the rungs from measured chance line through stateless floor to full retainer, what each rung's curve should look like, and the two rungs whose knobs are calibrated to the task schedule. |
| [`phased-store-removal.md`](phased-store-removal.md) | The phased store-removal protocol: a single reset placed at the train/probe boundary to measure what migrated into durable state, vs the uniform-reset sweep. |

## Repo tour (suggested reading order)

The code is small enough to read whole. A sensible order, smallest and most
self-contained first — each module's docstring carries its own rationale, and
each `tests/test_<module>.py` doubles as executable documentation of the
contract:

1. [`../retention_bench/scoring.py`](../retention_bench/scoring.py) — pure metric
   math: the band formula, relative ε, post-reset windows, bootstrap CIs.
2. [`../retention_bench/reset_schedule.py`](../retention_bench/reset_schedule.py)
   — when a run hard-resets: one protocol, three schedules.
3. [`../harness/sut_process.py`](../harness/sut_process.py) and
   [`../harness/dir_lifecycle.py`](../harness/dir_lifecycle.py) — process/container
   launch, the JSONL wire contract, kill semantics, survive-dir accounting.
4. [`../retention_bench/system.py`](../retention_bench/system.py) — the heart:
   `SubprocessSystem`, which presents a process-contract SUT to CL-Bench and
   owns the hard-RESET bounce.
5. [`../retention_bench/gain_curve.py`](../retention_bench/gain_curve.py) — the
   three-arm sweep, the reset-axis curve, and the CLI.
6. [`../retention_bench/_clbench.py`](../retention_bench/_clbench.py) — the single
   import chokepoint onto CL-Bench.
7. One reference SUT: [`../suts/associative_memory/`](../suts/associative_memory/)
   is the cleanest (keyless JSON state, exact-scored); then
   [`../suts/constructive/`](../suts/constructive/) for the train-and-grow seam.
8. [`../retention_bench/tasks/symbolic_associative_retention.py`](../retention_bench/tasks/symbolic_associative_retention.py)
   — the first Retention-Bench-native task.

Run `./run.sh smoke` while reading: it drives a keyless reference SUT through
the full sweep offline and prints the curve the docs describe.

> **History.** retention-bench began life as a standalone benchmark (working name
> "CL-N") before the 2026-06 pivot onto CL-Bench. Those earlier standalone-era
> specs — and the pivot/triage decision records — are retained on the `dev` branch
> under `docs/archive/` for "why" archaeology; they are superseded and
> intentionally not part of the public docs.
