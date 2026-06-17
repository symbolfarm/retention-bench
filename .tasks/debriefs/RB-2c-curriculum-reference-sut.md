# Debrief: RB-2c Curriculum reference SUT, gain-curve smoke, and docs

**Completed:** 2026-06-17
**Commit:** 62b4463

## What shipped

Added `suts/associative_memory`, a keyless JSON-state reference SUT for
`symbolic_associative_retention`. It parses train prompts, persists object
attributes and attribute-to-bin rules in `associations.json`, and answers recall
and transfer probes from that survive-dir state.

Added `tests/test_associative_memory_clbench.py`, which drives the SUT through
`retention_bench.gain_curve` and asserts a non-excluded retention band. Updated
`docs/associative-curriculum.md` and `TASKS.md` to point at the landed substrate.

The documented smoke command prints:

- `P = 0.0000`
- `C = 0.6154`
- `C - P = 0.6154`
- `every_2`: `R(k) = 0.6154`, `norm_gain = 1.000`
- `every_1`: `R(k) = 0.6154`, `norm_gain = 1.000`

## Descoped / deferred

Repeated-exposure schedules and sample-efficiency metrics remain RB-3. No
constructive-retention model changes landed here.

## Design decisions

- Kept the reference SUT stdlib-only and parseable from the rendered prompt so it
  exercises the same subprocess contract as other SUTs.
- Used `"unknown"` for missing recall/transfer state. This gives the wiped prior
  deterministic zero probe reward without adding special task-side handling.
- Flushed `associations.json` before every reply so hard-reset kills cannot lose
  acknowledged state.

## Observations

The new task's unscored train/context instances mean the perfect-reference
ceiling is `16/26 = 0.6154`, not `1.0`. This is expected and documented; probe
metrics remain the curriculum headline.

## Follow-ups

### Filed as tasks

- **RB-3** Repeated-exposure curriculum variant — add exposure-count schedules
  and sample-efficiency metrics on top of this one-shot substrate.
