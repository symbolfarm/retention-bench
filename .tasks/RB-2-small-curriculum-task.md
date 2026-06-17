# RB-2 Small curriculum task for constructive retention

**Priority:** high
**Blocked by:** nothing
**Touches:** `retention_bench/`, `tests/`, `docs/`, `TASKS.md`

## Context

The CL-Bench pivot made `blind_spectrum_monitoring` the fastest integration
target for Retention Bench, but Toby's constructive neural network research needs
a smaller developmental substrate first: TinyStories-scale or smaller models that
are genuinely deficient in basic skills, then learn through a controlled
curriculum.

The existing C6 task asked for a constructive-friendly CL-Bench task only if the
adopted CL-Bench tasks lacked the needed signal. That premise is now stale. BSM
remains useful for external validity, but the first research loop should use a
deterministic, small-scale curriculum where the absent skill, retained structure,
and held-out transfer target are explicit.

## Goal

Add the first Retention Bench-owned curriculum task that can be driven by the
existing `SubprocessSystem` / gain-curve machinery and gives
`constructive-retention` a small, non-frontier M2 target.

## Acceptance criteria

- [ ] Implement a deterministic CL-Bench-compatible `ContinualLearningTask`
      for a small curriculum target, initially one of:
      associative retention, compositional retention, or a tiny generated world
      model.
- [ ] The task exposes curriculum phases and separates training/context
      instances from held-out or novel recombination probes.
- [ ] Scoring is exact and deterministic; no LLM judge or frontier-agent harness
      assumptions are required.
- [ ] The task has a legible retention band: a simple stateful reference SUT
      beats the stateless prior, and `retention_bench.gain_curve` can run it.
- [ ] The reported result distinguishes at least a memorization/shallow-recall
      component from a transfer/generalization component, even if the first
      implementation only reports both in task metadata.
- [ ] Tests cover task determinism, schema validation, scoring, and one
      end-to-end gain-curve smoke.
- [ ] Docs or task notes explain how this target differs from BSM and why it is
      the first constructive-retention M2 substrate.

## Relevant files

- `retention_bench/system.py`
- `retention_bench/gain_curve.py`
- `retention_bench/reset_schedule.py`
- `tests/test_subprocess_system.py`
- `scratch/c0-spike/run_spike.py`
- `/home/agent/src/cl-bench/src/tasks/` for task interface references

## Decisions already made

- BSM stays as an external-validity / CL-Bench integration target, not the first
  model-development substrate.
- The first curriculum target should be small-model-first and deterministic,
  with exact scoring.
- Replay-disabled / parametric-retention claims should remain separate from
  replay or notes baselines.

## Out of scope

- Implementing constructive-retention model changes.
- Reworking the process/SUT protocol.
- Multi-step agentic task support.
- LLM-generated large corpora; frontier models may help later author curricula,
  but the first task should be procedurally reproducible.
