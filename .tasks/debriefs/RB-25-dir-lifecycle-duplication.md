# Debrief: RB-25 Resolve the two survive-dir creation paths

**Completed:** 2026-09-11
**Commit:** 273f797

## Design decisions

- **Option 3 (remove), not option 2 (document as spec).** The brief framed
  `dir_lifecycle` as "currently acting as a reference implementation that a test
  pins the live path against", which is the strongest argument for keeping it.
  Reading both paths, that framing does not hold: `create_dir(parent)` built
  `<parent>/dir` and `shutil.rmtree`'d any existing copy. `SubprocessSystem`
  takes the survive-dir path as *given* and creates it with `exist_ok=True`,
  because the state surviving the SIGKILL is the measurement. The two never
  shared creation semantics — only the `.harness/` reservation. A "reference
  implementation" that a reader could follow into an `rmtree` of the survive-dir
  is worse than no reference, so documenting it as a spec would have made the
  comprehension hazard official.
- **Option 1 (make it live) was rejected for the same reason**, and it is worth
  recording that it was the option the brief listed first: wiring `create_dir`
  into `SubprocessSystem.__init__` would destroy the survive-dir on construction
  and silently turn every retention arm into a stateless one. It would not have
  failed loudly — `P` and `R(k)` would simply have converged.
- **The drift test was rewritten, not deleted.** It now asserts the property the
  parity was a proxy for: a file written under `.harness/` accounts as zero bytes,
  and a file written beside it accounts as itself. That is strictly stronger than
  "matches a helper nothing calls", and it survives the helper's removal.
- `account_dir` and `HARNESS_RESERVED_PREFIX` stay: both are live, called from
  `system.py` in three places.

## Descoped / deferred

- **`snapshot_dir`'s tar.gz capability is gone with no replacement.** It was
  listed as a REUSE target in the pivot plan (`docs/archive/clbench-pivot-plan.md`)
  as the "storage-delta signal"; what actually got used for that is `account_dir`.
  If a run ever needs to archive a survive-dir for post-hoc inspection, write it
  then, against a real caller — `git show 273f797^:harness/dir_lifecycle.py` has
  the old implementation.

## Observations

- **The repo `.venv` was dead on arrival** and healing it is a documented
  two-liner (`AGENTS.md` "Python"): `uv python install 3.13` restores the dangling
  interpreter symlink, then reinstall the editable `cl-benchmark` pin. Only
  `/workspace` is host-backed, so the uv-managed interpreter does not survive a
  container rebuild. Do this first; nothing in the test suite runs without it.
- `cl-benchmark`'s importable top-level package is **`src`**, not `cl_benchmark` —
  `import cl_benchmark` fails on a perfectly healthy install. Check
  `from retention_bench import _clbench` instead.
- Full suite is ~314 tests and runs in well under a minute; `./run.sh smoke` is
  the end-to-end check and takes about the same. Both were run before and after.
- The 2026-07-07 v0.1 review (`docs/reviews/`) had already flagged this drift from
  the other direction — "`__init__` doesn't create the `.harness/` reserved dir".
  RB-13 fixed it by *adding* the mkdir plus the parity comment, which is what
  created the appearance of a reference implementation this task removed.

## Follow-ups

### Considered and dropped

- **Retiring `harness/` as a package** (it is now two modules, one of which is 40
  lines). Not worth a task: `sut_process` is substantial and the import path
  `from harness import ...` appears across tests and docs. A rename buys nothing.
- **Updating `docs/archive/clbench-pivot-plan.md`**, which still lists the tar.gz
  snapshot as a reuse target. It is in `docs/archive/` and reads as a historical
  plan; correcting archived plans to match what happened erases the record of what
  was planned.
