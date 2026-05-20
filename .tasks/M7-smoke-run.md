# M7 End-to-end smoke run

**Priority:** medium
**Blocked by:** M4, M5, M6
**Touches:** `run.sh`, `docs/` (run-log or README updates as needed)

## Context

The MVP milestone. Take the M5 smoke-test task definition, run it through the M4-validated harness + no-state SUT integration, score the resulting trace with M6, and produce a printed `P`/`C`/`R(k)` retention curve. End-to-end, no manual stitching.

This is the proof that retention-bench is operational — that a SUT developer could, in principle, fork the repo, plug in their own SUT conforming to the M3 contract, and produce a leaderboard-shaped result.

## Goal

`./run.sh smoke` (or equivalent single command) executes the smoke-test task end-to-end on the no-state SUT and prints the retention curve.

## Acceptance criteria

- [ ] A single command runs the full pipeline: load M5 task → drive M4 harness + SUT → write trace + snapshots → run M6 scorer → print retention curve.
- [ ] No manual steps between harness exit and scorer invocation.
- [ ] Output is reproducible in shape (not in exact `sut_answer` strings, since LLMs aren't deterministic): the retention table prints the same questions in the same order with valid `P`/`C`/`R(1)` values every run.
- [ ] A short run-log appendix in `docs/` (or `tasks/smoke-test/sample-output.md`) capturing one example invocation's output, so future agents can compare against a known-good shape.
- [ ] README.md updated with a "Quickstart" section pointing at the smoke-test command.
- [ ] Resource appendix fields (wall_clock, tokens_in/out, model_id, api_call_count) are populated in the trace.

## Relevant files

- All M1–M6 artifacts.
- `README.md` — needs a Quickstart pointer.

## Decisions already made

- No-state SUT only for MVP smoke (#11B; notes-LLM + naive-RAG are B1, B2).
- Exact-match scoring only (#6A surface-facts component).
- Public-domain text from M5.

## Out of scope

- Multiple SUTs in one run (post-MVP).
- Leaderboard rendering (post-MVP).
- CI integration — local smoke run is sufficient for MVP.
- Container packaging (B4).
- Performance / cost optimisation.

## Notes for the implementer

- The "single command" can be a thin wrapper script (`run.sh smoke` → `python -m harness tasks/smoke-test/task.yaml && python -m scorer runs/latest/trace.jsonl`). Don't over-engineer.
- This task is the natural place to surface "what did we miss in M1–M6?" — any seam that requires manual reconciliation between trace output and scorer input is a candidate retroactive patch to M1, M2, or M6. Note these in the debrief; small patches land here, large patches get filed as follow-up tasks.
- Once this runs green, the MVP is *done*. Backlog (B1–B8) can be prioritised against next-step research goals at that point.
