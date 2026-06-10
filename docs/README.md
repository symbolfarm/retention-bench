# Documentation

retention-bench extends [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)
(Asawa et al.) with a hard **RESET** (a process-kill discontinuity across which
only an on-disk survive-directory persists) and a **constructive/parametric**
system class. These docs describe the current design.

| Doc | What it covers |
|---|---|
| [`clbench-pivot-plan.md`](clbench-pivot-plan.md) | Why retention-bench is an extension on top of CL-Bench rather than a standalone benchmark; what we reuse vs. contribute. Start here. |
| [`metrics.md`](metrics.md) | The retention metric — normalised `(R − P) / (C − P)`, the reset (`k`) axis, the `C ≈ P` exclusion rule, and reconciliation with CL-Bench's gain. |
| [`sut-interface.md`](sut-interface.md) | The system-under-test process contract (how a SUT reads stages, mutates the survive-dir, and reports), and the subprocess / container launch modes. |
| [`clbench-task-triage.md`](clbench-task-triage.md) | Triage of CL-Bench's tasks for cross-reset purity, shape, and the understanding signal. |
| [`constructive-sut-development-brief.md`](constructive-sut-development-brief.md) | Design of the constructive (train-and-grow) reference SUT and its compute accounting. |

> **History.** retention-bench began life as a standalone benchmark (working name
> "CL-N") before the 2026-06 pivot onto CL-Bench. Those earlier standalone-era
> specs are retained on the `dev` branch under `docs/archive/` for "why"
> archaeology; they are superseded and intentionally not part of the public docs.
