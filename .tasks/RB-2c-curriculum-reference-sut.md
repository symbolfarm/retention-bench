# RB-2c Curriculum reference SUT, gain-curve smoke, and docs

**Priority:** high
**Blocked by:** RB-2b
**Touches:** `suts/`, `retention_bench/`, `tests/`, `docs/`, `TASKS.md`

## Context

RB-2b adds the deterministic associative curriculum task. Before using it as a
constructive-retention substrate, Retention Bench needs to prove that the task
has a legible retention band under the existing hard-reset machinery: a simple
stateful system should beat the wiped stateless prior, and `gain_curve` should
render a defined curve.

The reference SUT is deliberately not the constructive SUT. It is a small JSON
state baseline that demonstrates task mechanics and gives future model work a
known-good comparison.

The implementation spec is `docs/associative-curriculum.md`.

## Goal

Add the stateful JSON reference SUT, an end-to-end gain-curve smoke test, and
short docs explaining why this curriculum differs from BSM and how it supports
the constructive-retention M2 loop.

## Acceptance criteria

- [ ] A keyless reference SUT persists taught associations in the survive-dir and
      answers recall/transfer probes from that persisted state.
- [ ] With `wipe_on_reset=False`, the reference SUT beats the stateless prior on
      probe instances; with `wipe_on_reset=True`, probe performance collapses as
      specified by RB-2a.
- [ ] `retention_bench.gain_curve` can run the reference SUT on the new task and
      produce a non-excluded band.
- [ ] Tests include one end-to-end gain-curve smoke using the reference SUT.
- [ ] Docs or task notes explain how the target differs from
      `blind_spectrum_monitoring`, why it is the first constructive-retention M2
      substrate, and what it does not claim.
- [ ] `TASKS.md` is updated to reflect the new current substrate state.

## Relevant files

- `suts/`
- `docs/associative-curriculum.md`
- `retention_bench/gain_curve.py`
- `retention_bench/system.py`
- `tests/`
- `docs/`
- `TASKS.md`

## Decisions already made

- The reference SUT should be simple JSON state, not the constructive SUT.
- The retention-band proof belongs with the reference SUT and gain-curve smoke,
  not in the task-only implementation.
- Probe/component metrics should stay visible so easy train/context instances do
  not hide the actual retention signal.

## Out of scope

- Constructive-retention model changes.
- Repeated-exposure / sample-efficiency variants.
- True RL reward-feedback loops.
