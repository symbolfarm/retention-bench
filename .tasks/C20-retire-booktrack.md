# C20 Retire the book-track — make the CL-Bench-native smoke the only path

**Priority:** high
**Blocked by:** C19
**Touches:** `run.sh`, `harness/` (partial), `scorer/` (partial), `tasks/smoke-test/`, `docs/`, `docs/archive/`, `README.md`, `TASKS.md`, `tests/` (retire 5 files), possibly `suts/no_state` + `suts/naive_rag`

## Context

The repo straddles two paths (see C18 debrief Observations): the legacy
**book-track** harness (`./run.sh smoke` → `python -m harness` + `python -m
scorer` over `tasks/smoke-test/`) and the **CL-Bench extension**
(`retention_bench/`: `SubprocessSystem`, `gain_curve`). The README headline (C14)
already commits to the extension, but the runnable quickstart still drives the
book-track — narrative and demo contradict. Decided this session: **Path-2-only**.
C19 builds the keyless BSM accumulator SUT that lets the smoke run CL-Bench-native
and offline; this task pulls the book-track out and repoints everything at it.

**Keep-set (verified by import scan):** `retention_bench/` imports *only*
`scorer.aggregate` (`EPSILON`, `normalised_retention`) and `harness.dir_lifecycle`
+ `harness.sut_process`. Those three files stay. Everything else in `harness/` and
`scorer/` is book-track and retires — **but verify each file has no live importer
in `retention_bench/` before deleting it.**

## Goal

`./run.sh smoke` runs the C19 SUT through `gain_curve` on `blind_spectrum_monitoring`
offline (no key), printing the `P`/`C`/`R(k)` curve; the book-track harness/scorer
code, its tests, the `tasks/smoke-test/` fixture, and the now-orphaned schema docs
are gone; README/docs/TASKS reflect a single CL-Bench-native path.

## Acceptance criteria

- [ ] `./run.sh smoke` repointed to `python -m retention_bench.gain_curve --task
      blind_spectrum_monitoring --sut "<C19 SUT>" --extra-pythonpath <its dir>`
      (small `--reset-every` sweep), printing the curve. Runs offline, keyless.
- [ ] `run.sh` fallthrough (`exec python3 -m harness "$@"`) repointed to the
      `gain_curve` arbitrary-task entry (or removed if no longer meaningful).
- [ ] **Retire the book-track code**, after confirming no live importer:
      `harness/event_loop.py`, `harness/task_loader.py`, `harness/trace_writer.py`,
      `harness/__main__.py`, `scorer/judge.py`, `scorer/exact_match.py`,
      `scorer/curve.py`, `scorer/__main__.py`, `tasks/smoke-test/`. **Keep:**
      `harness/sut_process.py`, `harness/dir_lifecycle.py`, `scorer/aggregate.py`
      (+ whatever `aggregate` itself imports — check `scorer/protocols.py`).
- [ ] Retire the 5 book-track test files (`test_event_loop_integration`,
      `test_scorer_exact_match`, `test_scorer_judge`, `test_task_loader`,
      `test_trace_writer`) and check `test_docker_launch.py`'s inline echo SUT
      isn't depending on a retired module.
- [ ] **Re-archive** `docs/trace-schema.md` + `docs/task-definition-schema.md` to
      `docs/archive/` (C18 un-archived them solely to serve the book-track
      quickstart). Fix `docs/sut-interface.md` cross-refs, `docs/README.md` index,
      and the root README "Documentation" section so nothing links into a void.
- [ ] README Quickstart + "How retention is scored" rewritten for the gain-curve
      smoke (the no-state-as-floor framing is book-track-specific; the floor is now
      the intrinsic `P` arm).
- [ ] `TASKS.md` updated: book-track moves from "superseded historical" to
      actually retired.
- [ ] `pytest` passes; `scripts/promote.sh dryrun` clean (public tree coherent,
      no dangling links, no archived docs leaking to `main`).

## Decisions to confirm with Toby (do not bake silently)

- **Disposition of `suts/no_state` + `suts/naive_rag`.** Both speak *only* the
  book-track contract (no `clbench_main`); `notes_llm` + `constructive` are
  already CL-Bench-native. The pivot plan marked all three DEPRIORITIZE
  (duplicate CL-Bench's stateless / Mem0 / ICL-Notepad). `gain_curve`'s `P` arm
  already provides the stateless floor intrinsically. **Recommendation: drop both
  with the book-track** and update the README reference-SUT list to
  `notes_llm` + `constructive` (+ the keyless BSM accumulator). Confirm before
  removing — it is a public-story change. *[Toby's answer: TBD]*

## Relevant files

- `run.sh`, `README.md`, `TASKS.md`, `docs/README.md`, `docs/sut-interface.md`,
  `docs/trace-schema.md`, `docs/task-definition-schema.md`, `PUBLIC_PATHS`,
  `scripts/promote.sh`.
- `harness/`, `scorer/` (partial retirement — see keep-set above).
- `tests/` (5 book-track files + `test_docker_launch.py` check).

## Decisions already made

- Path-2-only (this session). Keep-set is `scorer.aggregate` +
  `harness.{sut_process,dir_lifecycle}` — verified by import scan.
- Demote-then-delete sequencing: the smoke replacement (C19) lands *before* the
  deletions here, so a working keyless smoke exists throughout.

## Out of scope

- Building the smoke SUT (C19).
- Wiring the constructive SUT as a slower `./run.sh demo` (optional follow-up;
  `constructive.clbench_main` already exists, so it's a tiny run.sh add — file
  separately only if Toby wants it).
- The orphan-`main` cutover (C17). **Note:** C20 changes the public quickstart
  C17 would snapshot, so C17 must not run before C20 — add C20 to C17's
  `blocked_by` when filing.
