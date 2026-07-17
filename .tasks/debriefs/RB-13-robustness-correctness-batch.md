# Debrief: RB-13 Robustness & correctness batch

**Completed:** 2026-07-17
**Commit:** 68bb663

## What shipped

All seven acceptance-criteria checkboxes, in one commit:

1. **Sweep context manager** — `run_reset_sweep`'s `_run` helper now does
   `with make_system(...) as system:` so the final process/container per arm
   (ceiling, prior, and every stateful arm) is reaped deterministically
   instead of relying on the weakref finalizer under GC delay/exceptions.
   `k` is captured (`system.scheduled_resets`) inside the `with` block before
   the system is torn down.
2. **`--stderr-log` exposed and defaulted on** — new CLI flag
   (`--stderr-log`, default `sut-stderr.log`), resolved relative to each
   arm's own per-arm state dir (`state_dir / args.stderr_log`) and passed as
   `SubprocessSystem(..., stderr_log=...)`. Empty string disables it
   (`DEVNULL` passthrough).
3. **Env-var knobs fail loud** — `reset_lossy._rate()` and
   `bounded_memory._cap()` now raise `ValueError` with a clear message on
   both non-numeric and out-of-range input, instead of silently returning
   the default. Docstrings updated to match.
4. **`_split_reply` error taxonomy** — replaced `reply.get(key) or {}` with
   an explicit-default form so a *present* falsy non-dict `resource` (`0`,
   `""`, `false`) hits the `isinstance` check and raises `SUTError`, rather
   than being masked into `{}` before the check runs. An explicit `null` is
   still treated as "no resource reported" (same as the key being absent).
   `respond()` now also wraps a schema-nonconforming `action` (a pydantic
   `ValidationError` from `query.response_schema(**action_fields)`) in
   `SUTError`, so both malformed-reply failure modes surface at the same
   error-taxonomy level.
5. **`r_max` per-instance-schedule** — `SymbolicAssociativeRetentionTask`
   now computes `self.r_max` in `build_canonical_run_state` from the actual
   built instance list (`scored_count / total_count`), shadowing the
   class-attribute default. `num_exposures=2` now correctly yields 16/36
   instead of the stale 16/26. The class attribute stays (documented as
   "default schedule only") since it's still the natural default for anyone
   reading the class before instantiating.
6. **`.harness/` dir-creation parity** — `SubprocessSystem.__init__` now
   creates `state_dir / dir_lifecycle.HARNESS_RESERVED_PREFIX` right after
   `mkdir`, matching `dir_lifecycle.create_dir`.
7. **Book-track dead code** — removed `send_event` from
   `harness/sut_process.py` (confirmed its only caller was
   `tests/test_docker_launch.py:159`); demoted it to a test-only helper
   `_send_event` in that file (see "Design decisions" below). Removed the
   legacy `entrypoint` field from all seven `suts/*/sut-manifest.json`
   files and its mentions in `docs/sut-interface.md`,
   `retention_bench/system.py`'s `ContainerLaunch` docstring,
   `suts/constructive/README.md`, and comments in
   `tests/test_constructive_container_clbench.py` /
   `tests/test_sut_process_launch.py`. Grepped for any live-path consumer of
   the manifest field before deleting — none found; `docs/sut-interface.md`
   already documented that the live harness never parses the manifest at
   all (only `clbench_entrypoint` is a "keep in sync" convention for
   humans).

Also updated `harness/sut_process.py`'s module docstring (previously showed
the retired READ/QUIZ wire example as if live) to describe what the module
actually does now: process-lifecycle primitives only, wire framing lives in
`retention_bench.system`.

## Descoped / deferred

Nothing from the seven checkboxes. Two items explicitly out of scope per the
task brief and left untouched: `torch.load(weights_only=False)` in
`checkpoint.load`, and `sut_kit` reference-SUT de-duplication.

Did **not** touch the constructive/notes_llm SUTs' standalone book-track
`__main__.py` entrypoints (`python -m constructive`, `python -m notes_llm`)
or their READ/QUIZ framing — those are a much larger surface than the single
`entrypoint` manifest field and `send_event` helper the brief named, and
removing them isn't part of RB-13's Touches set. Left a couple of doc
mentions ("book-track entrypoint" in READMEs) intact since they refer to
this still-present code, just reworded the ones that specifically cited the
now-removed manifest field.

## Design decisions

- **`send_event`: demoted to a test helper, not rewritten against `_exchange`.**
  The brief offered both options. Rewriting `test_docker_launch.py`'s docker
  round-trip test against the live per-instance JSON contract would also
  require rewriting the inline `_ECHO_SUT` script (currently speaks
  READ/QUIZ) and picking a `response_schema`/task-shaped request — more
  surface change for a test whose actual point is launch/kill/teardown
  correctness on the docker path, not wire-protocol coverage (that's already
  covered elsewhere, e.g. `test_subprocess_system.py`'s counter-SUT tests).
  Moving the exact function into the test file as `_send_event` preserves
  the existing echo SUT and test assertions unchanged, and is honestly
  labelled as a demoted test-only helper in both its own docstring and the
  `harness/sut_process.py` module docstring that now points at it.
- **`r_max`: instance attribute shadows the class attribute, not a
  `@property` or removal.** CL-Bench's `registry.register_task` decorator
  (in the upstream `cl-benchmark` package) requires `r_max` to be a plain
  numeric value in `cls.__dict__` at *registration* time — a `@property`
  would fail that check. Our task isn't registered via that decorator
  (it's exposed through `retention_bench.tasks.LOCAL_TASKS` instead), so
  this constraint doesn't bind today, but keeping a real numeric class
  attribute costs nothing and stays safe if a future refactor does register
  it upstream-style. The instance attribute set in
  `build_canonical_run_state` shadows the class attribute per normal Python
  attribute lookup rules — no metaclass or property tricks needed.
- **Only `reset_lossy` and `bounded_memory` env knobs were hardened**, not
  every env-var read in the SUT ladder. The brief named these two
  specifically ("`RESET_LOSSY_RATE`, `BOUNDED_MEMORY_CAP` (and peers)").
  The constructive SUT's `CONSTRUCTIVE_*` int knobs (`_int` helper) already
  fail loud on non-numeric input (`int(v)` raises uncaught) — they just
  don't validate range invariants (e.g. negative `n_layers`), which is a
  smaller and different gap than the "catches ValueError and returns the
  default" pattern the brief is about. Left them as-is to keep the diff
  scoped to the named knobs; flagged below as a considered-and-dropped
  follow-up rather than silently expanding scope.
- **`--stderr-log` is a filename, not a path-or-off boolean.** Chose
  "filename relative to each arm's state dir, empty string disables" over a
  boolean flag + fixed name, so a user sweeping many arms in one `gain_curve`
  invocation still gets per-arm-isolated stderr files without extra plumbing
  (the CLI's `make_system` closure already receives `state_dir` per arm).

## Observations

- Getting a clean pytest summary line out of this sandbox's Bash tool proved
  oddly flaky — `-q` runs consistently truncated the final "N passed, M
  skipped" line even to a file. `-v` (verbose per-test dots-with-filenames)
  did print the summary reliably; used that to confirm the final count
  (111 passed, 2 skipped, up from the 93/2 baseline — 18 new tests, all
  green). Worth remembering for future sessions in this same environment.
- The `entrypoint` field removal was lower-risk than it looked at first
  grep: `docs/sut-interface.md` already stated up front that "the live
  harness does not read `sut-manifest.json`" at all, so the field was
  purely documentation-of-history with zero live consumers — confirmed via
  `grep -rn "entrypoint"` across `.py`/`.json`/`.md` before touching
  anything, per the brief's explicit stop-and-report instruction if that
  grep had turned up a live consumer.
- The worktree had been branched from the orphan `main` snapshot instead of
  `dev` (same issue two sibling agents hit) — required `git reset --hard
  dev` as the very first step before any of the above.

## Follow-ups

### Considered and dropped

- **Constructive SUT's `CONSTRUCTIVE_*` env knobs range-validation** — they
  already fail loud on non-numeric input via an uncaught `int()`
  `ValueError`; adding range checks (e.g. `n_layers >= 1`) would be a
  reasonable small hardening pass but is a different (smaller) gap than the
  one this task's checkbox named, and touching them wasn't in the brief's
  Touches set. Not filed as a task — small enough to fold into any future
  pass that touches `suts/constructive/constructive/clbench_main.py`.
- **Rewriting `test_docker_launch.py`'s round-trip test against the live
  wire contract** — considered as the alternative to demoting `send_event`;
  dropped in favor of the demotion for the reasons in "Design decisions"
  above. If a future task wants that test to also exercise the live
  contract (not just launch/kill), it should build a small purpose-written
  echo SUT that speaks `{"prompt", "response_schema", ...}` /
  `{"action", "resource"}` rather than repurposing this one.
