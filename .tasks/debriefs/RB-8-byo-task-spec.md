# Debrief: RB-8 Bring-your-own task via --task-spec

**Completed:** 2026-06-28
**Commit:** f7156c0

## What shipped

`--task-spec TARGET:ClassName` on the gain-curve CLI — dynamic-import discovery
for CL tasks, so a task no longer has to be registered in `LOCAL_TASKS` (i.e. no
longer requires editing retention-bench).

- `load_task_spec(spec)` in `_clbench.py`: `TARGET` is a dotted module path
  (`importlib.import_module`) or a `.py` file path (`spec_from_file_location`);
  resolves `ClassName` and validates it's a `ContinualLearningTask` subclass.
  Raises actionable `ValueError`/`FileNotFoundError`/`ImportError`/`AttributeError`/
  `TypeError`; the CLI maps these to `parser.error`.
- `--task` and `--task-spec` are a mutually-exclusive group; exactly one is
  required (after `--list-tasks` short-circuits). `name` defaults to the class
  label from the spec when `--task-spec` is used.
- README "Bring your own task" section.

## Why

The task *interface* (`ContinualLearningTask` ABC) was already plugin-ready; only
*discovery* was hardcoded. Forcing experiment-specific tasks into the public
harness pollutes the `promote.sh` orphan-main snapshot and breaks
one-task-one-repo. BYO-task lets the episodic-memory composition task live in
constructive-retention instead. The task runs in the harness interpreter, so BYO
files must stay torch-free.

## Decisions

- Dynamic import now; setuptools entry-points deferred (heavier, tangles with the
  harness/SUT cross-venv install story). Recorded in the meta-research episodic
  idea-tree (D7 turn).
- File-vs-module heuristic: treat `TARGET` as a file if it ends `.py`, contains a
  path separator, or starts with `.`; otherwise a dotted module.
- Loader raises real exceptions (testable); only the CLI converts to SystemExit.

## Verification

- `pytest tests/test_gain_curve.py` — 17 pass (8 new: file load, module load,
  missing-colon, missing-file, non-task-class, CLI resolves spec, CLI rejects
  both flags, CLI requires a task).
- `pytest tests/test_symbolic_associative_retention.py` — 7 pass (registered-task
  resolution unaffected).
- Real end-to-end: `--task-spec retention_bench.tasks.symbolic_associative_retention:SymbolicAssociativeRetentionTask`
  driving the `no_state` reference SUT → full sweep ran, floored at R=0 as
  expected.

## Follow-ups

- **RB-9 (phased reset) is mostly already built**: `--reset-at "O1,O2"`
  (`ExplicitBoundaries`) already places resets at exact ordinals, so the phased
  falsifier is `--reset-at "<train_phase_len>"` (reset once after consolidation,
  before probes). RB-9 shrinks to verify + document + the headline/robustness
  framing reshuffle (D7).
- **CR-8** can now ship its bijection composition task as a BYO `.py` in
  constructive-retention, loaded via `--task-spec`, with no further RB edit.
