# Debrief: M2 Harness skeleton (event loop + DIR lifecycle)

**Completed:** 2026-05-20
**Commit:** fff3ca0

## What shipped

- `harness/` package: `task_loader.py`, `dir_lifecycle.py`, `trace_writer.py`,
  `sut_process.py`, `event_loop.py`, `__main__.py`, `stubs/echo_sut.py`.
- `pyproject.toml` (Python 3.11+, PyYAML only) and `run.sh` wrapper.
- Event loop drives `READ`/`QUIZ`/`RESET` against a subprocess SUT using
  stdin/stdout JSONL framing (pre-locked decision).
- DIR lifecycle: fresh DIR per run; tar.gz snapshot per `RESET` with both
  uncompressed bytes and tarball size (#8C). `.harness/` prefix is reserved
  and excluded from accounting.
- Trace output matches `docs/trace-schema.md`: `trace.jsonl`, `questions.jsonl`,
  `stages/<event_id>.{in,out}`, `snapshots/reset-<event_id>.tar.gz`,
  `run-manifest.json`, `sut-manifest.json`.
- Per-question records with `<ANSWER id="...">` parsing
  (`ok` / `not_found` / `ambiguous`) and `question_seen_before` integer counter
  per decision #10B.
- Task-loader validates all 8 schema/semantic rules from
  `docs/task-definition-schema.md` (refuses to run an ill-formed task).
- 13 pytest tests covering trace writer shape, SUT-answer parsing,
  DIR accounting, snapshot tarball contents, task-loader validation, and
  an end-to-end stub run.

End-to-end smoke verified with `./run.sh` against the stub SUT: produces a
5-event trace + 3 per-question records + RESET snapshot + manifests.

## Descoped / deferred

Nothing from the M2 acceptance criteria descoped. Real SUT integration is M4;
scoring is M6; container packaging is B4 — all explicitly out of scope.

## Design decisions

- **SUT manifest discovery path.** Brief didn't specify how a SUT delivers its
  `sut-manifest.json`. I chose `DIR/.harness/sut-manifest.json`: the harness
  copies it into the run root at end of run if present, else writes a stub.
  This keeps the SUT-side contract minimal (write one file into a reserved
  DIR prefix) and avoids a second I/O channel. M3 should confirm; flip is cheap.
- **`event_id` naming.** Used `evt-NNNN` (4-digit zero-padded) per the trace
  schema's worked example. Run-id format: `<task_id>-<iso8601>-<sha1[:6]>`,
  also from the schema example.
- **Graceful end-of-run shutdown.** RESET kills with SIGKILL per the brief.
  At end-of-run I close stdin (EOF) and wait briefly, falling back to SIGKILL.
  The brief is silent on end-of-run shutdown; EOF-then-kill keeps stub-style
  SUTs from being unnecessarily SIGKILLed when there's no semantic need.
- **`PYTHONPATH` propagation in `spawn_sut`.** Because the SUT runs with
  `cwd=DIR`, a `python -m harness.stubs.echo_sut` command couldn't find the
  `harness` package. I inject the repo root into the SUT's `PYTHONPATH`. This
  is harness-internal plumbing; real-SUT commands (absolute paths or
  container entrypoints) won't notice. Worth flagging for M3 so they don't
  rediscover it.
- **`exit_status` taxonomy.** Used the four values listed in `trace-schema.md`
  (`ok` | `sut_crash` | `harness_error` | `timeout`). `timeout` is not yet
  reachable — the harness has no per-event timeout. Filing as candidate.
- **`material_refs` in QUIZ trace event** is computed as the sorted distinct
  set of question material refs at that QUIZ. Non-load-bearing detail not
  pinned by the schema; sorting is for determinism.

## Observations

- **Protocol-doc conflict resolved per instructions.** `docs/protocol.md` talks
  about "stages" and "sessions" and predates the `READ`/`QUIZ`/`RESET` event
  model — the schemas and decisions checklist supersede it. The M2 brief flagged
  this and I followed the schemas. Backlog item B6/B7 (rewrite `protocol.md` /
  `interface.md`) is already filed.
- **M3 has merged on `main` ahead of M2.** `suts/no_state/` exists and
  `docs/sut-interface.md` exists. M3's SUT contract is the input to M4's
  integration step; my stub stdin/stdout JSONL framing was the M2-pre-locked
  decision and should still be the contract M3 conforms to — but worth a
  cross-check at the start of M4.
- **`-9` exit code for SIGKILL'd SUT.** The integration smoke run reports
  `sut_exit_code: -9` for a SIGKILL'd process — that's Python's `Popen.wait()`
  convention (negative signal number). The schema permits "integer or null";
  consumers should treat negative as "killed by signal abs(n)".
- **PyYAML is a soft dep at runtime.** Imported eagerly in `task_loader.py`;
  any harness invocation without it fails with `ImportError`. Acceptable for
  MVP; the alternative (lazy import for testability) wasn't worth it.

## Follow-ups

### Filed as tasks

None filed — all follow-ups below are either drive-by candidates or
considered-and-dropped. None looked load-bearing enough to file pre-M4.

### Considered and dropped

- **Per-event SUT timeout.** Harness currently blocks forever on
  `stdout.readline()`. A pathological SUT can hang a run. The right fix is
  per-event wall-clock + soft-kill escalation, but the cohort-1 reference
  SUTs are all bounded-latency LLM calls; deferring until a real SUT
  motivates it.
- **`run-manifest.json` carrying `exit_status: harness_error` when the
  harness itself raises.** Currently the manifest is written inside the
  try-block, so a harness error means *no* manifest is written. Acceptable
  for now (run dir is still on disk and `sut-stderr.log` survives) but a
  better story would be a finally-clause that writes a partial manifest.
  Small but touches error-handling structure; flag if it bites.
- **Validation of agentic-only vs in-context two-leaderboard split (#7).**
  Out of scope for the harness skeleton; the harness is neutral by design.
  Will land naturally once the per-task tier/mode declaration is built.
- **Anything fancier than exact-match in the per-question records.** That's
  M6 (scorer).
