# Debrief: C0 CL-Bench integration spike

**Completed:** 2026-06-07
**Commit:** 9edfd93

## What shipped

A throwaway-but-kept spike (`scratch/c0-spike/`) that drives a `SubprocessSystem`
adapter through CL-Bench's real `src.runtime.runner.run_task`, using a mock
single-shot retention task (count instances seen). The adapter reuses
`harness.sut_process` spawn/kill verbatim. Three configs through the real runner:

- A: stateful, no reset -> score 1.0 (1 spawn, 0 kills)
- B: hard reset + survive-dir -> score 1.0 (5 spawns, 4 SIGKILLs; state survived)
- C: hard reset + wipe (stateless baseline) -> score 0.2; normalized gain 1.0

## Descoped / deferred

No real CL-Bench task and no API-backed system were run (didn't need keys or
their dataset setup to prove the seam). Productionizing is C2/C3.

## Design decisions

- **Mock task over a real one** for the spike: proves the adapter contract
  without their per-task `setup()` (dataset downloads) or provider keys.
- **Reused `harness.sut_process`** from /workspace via sys.path rather than
  reimplementing — directly validates the "sut_process IS the SubprocessSystem"
  reuse claim. It imported cleanly under py3.13 (pure stdlib).
- **Hard reset via `reset_between_instances=True`**: the runner calls
  `system.reset()` after each completed instance (runner.py:519-524). Our
  `reset()` does SIGKILL+respawn keeping the survive-dir = hard reset, no core
  change.

## Observations

- CL-Bench's package is importable as `src.*` (the distribution is literally
  named `src` — a packaging smell, but works).
- `Response.action` must be a pydantic model matching `query.response_schema`;
  the adapter builds it generically via `query.response_schema(**reply)`.
- **Key finding (feeds C2):** `reset_between_instances` is a *boolean* — resets
  after *every* instance (k=1 density only). A retention curve over `k` needs
  per-boundary control, which we own **system-side** by counting
  `instance_complete` in `observe()` and self-bouncing the process. So no
  upstream change blocks the k-axis; C7 PRs are nice-to-have, not prerequisites.
- `UsageEvent` is token/cost-shaped but has free-form `metadata`/`call_type`, so
  parametric FLOPs/storage accounting fits via `call_type="compute"` (-> C2/C3).
- Env: CL-Bench needs py>=3.13; system python is 3.12. Used `uv venv --python
  3.13` at `/home/agent/src/cl-bench/.venv` with `cl-benchmark` installed `-e`.

## Follow-ups

All captured in the C-series filing (C1-C7). No new tasks beyond those.
