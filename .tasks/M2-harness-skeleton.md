# M2 Harness skeleton (event loop + DIR lifecycle)

**Priority:** high
**Blocked by:** M1
**Touches:** `harness/`, `pyproject.toml`, `run.sh`

## Context

The harness is the thin process the retention-bench protocol runs in: it reads a task definition, drives the `READ`/`QUIZ`/`RESET` event loop, manages the SUT subprocess + persistent `DIR`, emits a JSONL trace + tarball snapshots, and exits. It does **not** interpret SUT-emitted directives (per the #7 resolution: thin harness; agentic SUTs handle their own tool calls; non-agentic SUTs get mock-transcript task variants).

This task builds the harness scaffolding without a real SUT — use a stub SUT (e.g. one that echoes back fixed text) for testing. M3 brings the no-state SUT; M4 wires them together.

## Goal

A Python module that, given a task-definition file, runs the full `READ`/`QUIZ`/`RESET` loop against a subprocess SUT, produces a valid trace + snapshots per the M1 schema, and terminates cleanly. Stub SUT for testing.

## Acceptance criteria

- [ ] `pyproject.toml` set up with Python 3.11+; dependencies kept minimal (stdlib + `anthropic` SDK will be added in M3, not here).
- [ ] `harness/` package with at least: `event_loop.py`, `dir_lifecycle.py`, `trace_writer.py`, `task_loader.py`, `__main__.py`.
- [ ] Event loop:
  - Loads a task-definition file (per M1 schema).
  - For each event: assembles `STAGE_INPUT` (tagged sections per decision #2A), writes to SUT stdin (or agreed I/O channel), reads `STAGE_OUTPUT`, records a JSONL trace entry.
  - On `RESET`: kills the SUT subprocess, snapshots `DIR` to a tarball under `snapshots/`, computes uncompressed bytes + file count + tar.gz size (decision #8C), spawns a fresh SUT process pointed at the same `DIR`.
- [ ] `DIR` lifecycle:
  - Created fresh at run start.
  - Persists across `RESET`s; the SUT may read/write within it.
  - Snapshotted per `RESET`.
  - Run-level cleanup behind a flag (default: keep for inspection).
- [ ] Trace writer:
  - Appends one JSONL record per event.
  - Emits per-`QUIZ` per-question records per M1 schema.
  - Resource appendix fields populated where measurable (wall_clock always; FLOPs/tokens left blank for stub SUT).
- [ ] Stub SUT included under `harness/stubs/` for self-testing. Trivial behaviour: echoes a fixed string on `QUIZ`, no-op on `READ`.
- [ ] `run.sh` wraps `python -m harness <task-definition.yaml>`.
- [ ] Basic pytest coverage for trace-writer record shape and DIR-snapshot bytes accounting.

## Relevant files

- `docs/trace-schema.md` (from M1) — the contract trace_writer.py must produce.
- `docs/task-definition-schema.md` (from M1) — the contract task_loader.py must consume.
- `docs/protocol.md` — `STAGE_INPUT`/`STAGE_OUTPUT` framing.
- `docs/decisions-checklist.md` (#1, #2, #7, #8) — relevant locked decisions.

## Decisions already made

- Python (TASKS.md stack note).
- Thin harness: does NOT parse SUT output for tool-call-shaped directives (#7 resolution). SUT-emitted text goes to the trace as-is; what the SUT did with `DIR` is its own business.
- Tagged-section `STAGE_INPUT` per #2A.
- `DIR` snapshots per `RESET`; both uncompressed bytes and tar.gz reported (#8C).
- API call counting is harness-external; for stub SUT it's N/A (no API calls). For M3+, count of subprocess invocations from the harness side is sufficient (no peek).

## Out of scope

- Real SUT integration (M3, M4).
- Scoring (M6).
- Container packaging (B4).
- Tier-declaration scaffolding (B4).
- LLM-judge integration (B3).

## Notes for the implementer

- SUT I/O channel: pipes vs. files. Default proposal: SUT reads `STAGE_INPUT` from a path the harness writes (e.g., `DIR/.harness/in`), writes `STAGE_OUTPUT` to another path the harness reads (`DIR/.harness/out`). File-based is simpler than pipes for subprocess that may be killed mid-stage. Confirm with M3's SUT contract; revise if pipes are cleaner.
- `RESET` is `process.kill()` + `wait()`, not graceful shutdown. The SUT should not assume it gets a chance to flush; anything in `DIR` is what survives.
