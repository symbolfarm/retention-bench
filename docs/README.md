# Documentation

retention-bench extends [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)
(Asawa et al.) with a hard **RESET** (a process-kill discontinuity across which
only an on-disk survive-directory persists) and a **constructive/parametric**
system class. These docs are the reference for building a system-under-test (SUT)
and interpreting its results; the project overview and quickstart are in the
[root README](../README.md).

| Doc | What it covers |
|---|---|
| [`sut-interface.md`](sut-interface.md) | The system-under-test process contract — how a SUT reads stages, mutates the survive-dir, reports, and is launched (subprocess / container). Start here if you're building a SUT. |
| [`task-definition-schema.md`](task-definition-schema.md) | The input contract: the YAML that tells the harness which `READ` / `QUIZ` / `RESET` events to run, against which materials and questions. |
| [`trace-schema.md`](trace-schema.md) | The output contract: the run-directory layout, the JSONL event stream, the per-question records, and the manifests the harness writes. |
| [`metrics.md`](metrics.md) | The retention metric — normalised `(R − P) / (C − P)`, the reset (`k`) axis, the `C ≈ P` exclusion rule, and reconciliation with CL-Bench's gain. |

> **Constructive SUT integration contract** — a dedicated requirements contract
> for constructive (train-and-grow) systems is in progress and not yet listed
> here; the `sut-interface.md` contract above already applies to constructive
> SUTs (a weights-mutating SUT is a valid `in-context` SUT).

> **History.** retention-bench began life as a standalone benchmark (working name
> "CL-N") before the 2026-06 pivot onto CL-Bench. Those earlier standalone-era
> specs — and the pivot/triage decision records — are retained on the `dev` branch
> under `docs/archive/` for "why" archaeology; they are superseded and
> intentionally not part of the public docs.
