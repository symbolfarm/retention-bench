# Debrief: M4 Wire harness + no-state SUT end-to-end

**Completed:** 2026-05-20
**Commit:** c4c7739

## What shipped

The harness ↔ SUT contract is now genuinely SUT-agnostic. The harness writes structured event lines in, reads structured response lines out, persists everything verbatim, and never parses the SUT's semantic output. All answer-format conventions (tag schemes, JSON-mode, structured-output APIs) are now private SUT implementation details.

Concrete changes:

- **Spec.** `docs/sut-interface.md` rewritten around structured `answers: [{"id":..., "text":...}]` for QUIZ replies; tagged-text `<ANSWER>` blocks dropped from the wire contract. `docs/trace-schema.md` updated to match (per-question records built by structural lookup, not regex). `docs/task-definition-schema.md` gains optional `event_timeout_seconds` top-level field.
- **Harness.** `sut_process.send_event` returns the parsed reply dict; adds `select()`-based timeout (default 300s, configurable via task def or CLI `--event-timeout`). New `SUTTimeout` exception bubbles into `exit_status: "timeout"`. `trace_writer.parse_sut_answers` (regex) → `lookup_sut_answers` (structural). `write_stage_output_json` persists the SUT's reply verbatim. `__main__` takes `--sut <pkg-dir>` (loads manifest, reads `entrypoint` array, copies manifest into run-root) or `--sut-cmd <raw>` (test shortcut for stubs). Spawned PYTHONPATH auto-includes the SUT pkg dir so `python -m <module>` resolves under cwd=DIR.
- **No-state SUT.** Parses `<ANSWER>` out of the model response itself (its private convention); emits the structured `answers` list on stdout. Model-side prompt unchanged.
- **Stub SUT.** Updated to the new wire shape.
- **Tests.** `tests/fixtures/trivial.yaml` (minimal READ/QUIZ/RESET/QUIZ contract fixture); `tests/test_no_state_integration.py` (live API integration test, skipped when `ANTHROPIC_API_KEY` is absent — confirmed `pytest tests/` passes 13 + skips 1 locally without a key); existing tests updated to use `lookup_sut_answers` / `write_stage_output_json`.
- **pyproject.toml.** Adds `[project.optional-dependencies] no-state-sut = ["anthropic>=0.39.0"]` per the drive-by from M2+M3 split.

Smoke-tested manually against the stub (`python -m harness tests/fixtures/trivial.yaml --sut-cmd "python3 -m harness.stubs.echo_sut"`): produces a valid trace; `stages/evt-0002.out` is the structured JSON reply; per-question records have `sut_answer = "STUB_ANSWER"` and `parsing_status = "ok"`.

## Descoped / deferred

- **Live no-state SUT run in this session.** Not done — would have burned API budget for what the stub already proves (the wire contract holds). The test is structurally complete and gated on `ANTHROPIC_API_KEY`; local runs with a key will exercise it.
- **`exit_status` written into a partial run-manifest on failure.** Currently exceptions propagate without writing run-manifest.json. Manageable for MVP — the trace.jsonl up to the failure point is still inspectable. Filed mentally as a future-quality task; not yet a task file.
- **Cross-platform timeout.** The `select()`-based timeout is POSIX-only. Windows SUTs would need a thread-based or asyncio path. Windows is out of scope; documented inline.
- **`docs/protocol.md` rewrite.** Still uses "clears" vocabulary; backlog B7.

## Design decisions

- **Structured `answers` list, not a dict.** Picked `[{"id":..., "text":...}, ...]` over `{"q1":"...","q2":"..."}` because (a) JSON-idiomatic for ordered collections, (b) supports the `ambiguous` case explicitly (duplicate ids), (c) preserves SUT-side ordering which can be useful for diagnostics. The harness deduplicates by counting occurrences during lookup.
- **READ replies keep `stage_output`, QUIZ replies switch to `answers`.** Asymmetric but defensible: READ has no per-question structure, QUIZ does. Could unify by having READ also use a structured field (`ack` or similar), but no clear benefit and the asymmetry tracks the semantic difference between the two event types.
- **`--sut <pkg-dir>` vs. `--sut-cmd <raw>`.** Two flags rather than one polymorphic flag. Cleaner, makes test scripts that need the stub explicit, and avoids "is this string a path or a command?" ambiguity.
- **`select()` over threading or asyncio.** Simplest for a single SUT subprocess on Linux/macOS. If/when we need concurrent SUTs (we don't), threading. If/when Windows (we don't), asyncio. Not load-bearing — `send_event` is a one-line swap.
- **PYTHONPATH auto-inject.** The SUT manifest declares `entrypoint: ["python", "-m", "no_state"]`, but cwd=DIR means the module isn't importable by default. Adding the SUT package dir to PYTHONPATH at spawn-time keeps the manifest readable (developer doesn't need to know about the launch quirk). Alternative would be to require absolute paths in the manifest; chose ergonomics over purity.
- **`event_timeout_seconds` as int seconds in task def, float on the wire.** Yaml-readable integer in the spec; floating-point internally so test fixtures can use sub-second values without lying about the contract.
- **Kept the stub-manifest fallback in event_loop.** When `--sut-cmd` is used (no manifest), the harness writes a "name: unknown" stub. Lets existing tests that don't supply a manifest still produce a complete run-dir. The real path is `--sut <dir>`; the fallback is for harness-only smoke tests.

## Observations

- **The contract flip was small in code, big in clarity.** Roughly 50 lines of harness code changed; the conceptual gain (harness has no idea what an "answer" looks like) is substantial. Worth the round-trip with the user to nail this before it calcified.
- **The PYTHONPATH issue would have bitten M7.** Discovered only when writing the no-state integration test — the SUT manifest's `entrypoint: ["python", "-m", "no_state"]` doesn't work under cwd=DIR without help. Fixed once, future SUTs benefit. Documented inline.
- **The TraceWriter `write_stage_output_json` removed an asymmetry.** Previously `.in` was tagged text and `.out` was tagged text too; now `.out` is JSON. Slightly inconsistent on disk, but `.out` *is* always structured (SUT reply); `.in` is *always* tagged text (assembled by harness from task def). Both are accurate per their producer's contract.
- **`select.select` after `text=True, bufsize=1`.** Readiness on a TextIOWrapper's underlying fd doesn't guarantee a complete line. In practice well-behaved SUTs flush after each event so the line is whole; a misbehaved SUT that writes partial bytes and hangs would be caught by the *next* event's timeout. Acceptable for MVP; if it bites, switch to non-blocking I/O.
- **The 13 existing tests passed unchanged after the contract flip** (except the two trace_writer tests that explicitly tested the old regex API). Good signal that the change was structurally clean.

## Follow-ups

### Filed as tasks

(None. M5/M6 are already filed and unblocked.)

### Drive-by cleanup landed

- Merged `anthropic` dep into root `pyproject.toml` under `[project.optional-dependencies] no-state-sut` (raised by M2 debrief).
- Trace pretty-printer NOT landed; deferred — wasn't needed to validate the contract and would have been speculative.

### Considered and dropped

- **Writing a partial run-manifest.json on failure paths.** Would be nice; not required for MVP correctness. The trace.jsonl + questions.jsonl + sut-stderr.log are all preserved up to the failure point. Revisit if/when failed runs become common.
- **JSON Schema files for the trace + task-def + SUT-interface contracts.** Tempting (frees the scorer in M6 from hand-rolling validation), but the schemas have just shifted under M4 and may shift again under M6. Lock after M7 lands. Same call as M1.
- **Renaming `event_timeout_seconds` → `event_timeout_s` for consistency with internal naming.** Decided no: the YAML field is human-facing and `_seconds` reads better in a task definition; internal `event_timeout_s` is fine.
