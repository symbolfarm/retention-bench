# Documentation

retention-bench extends [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)
(Asawa et al.) with a hard **RESET** (a process-kill discontinuity across which
only an on-disk survive-directory persists) and a **constructive/parametric**
system class. These docs are the reference for building a system-under-test (SUT)
and interpreting its results; the project overview and quickstart are in the
[root README](../README.md).

| Doc | What it covers |
|---|---|
| [`sut-interface.md`](sut-interface.md) | The system-under-test process contract — the `SubprocessSystem` one-line-JSON query/reply per CL-Bench instance, the survive-dir / hard-`RESET` mechanics, resource self-report, and launch (subprocess / container). Start here if you're building a SUT. |
| [`metrics.md`](metrics.md) | The retention metric — the reset-axis gain curve `norm_gain(k) = (R − P) / max(C − P, ε)`, the `C ≈ P` exclusion rule, and reconciliation with CL-Bench's gain. |
| [`associative-curriculum.md`](associative-curriculum.md) | Implementation spec for the first small constructive-retention curriculum task: deterministic symbolic associations, exact scoring, memorization-vs-transfer probes, and the repeated-exposure extension path. |

> **Constructive SUT integration contract** — a dedicated requirements contract
> for constructive (train-and-grow) systems is in progress and not yet listed
> here; the `sut-interface.md` contract above already applies to constructive
> SUTs (a weights-mutating, train-and-grow system is a first-class SUT — see
> "System class & leaderboard").

> **History.** retention-bench began life as a standalone benchmark (working name
> "CL-N") before the 2026-06 pivot onto CL-Bench. Those earlier standalone-era
> specs — and the pivot/triage decision records — are retained on the `dev` branch
> under `docs/archive/` for "why" archaeology; they are superseded and
> intentionally not part of the public docs.
