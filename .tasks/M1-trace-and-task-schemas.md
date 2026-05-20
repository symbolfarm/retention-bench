# M1 Trace + task-definition schemas

**Priority:** high
**Blocked by:** nothing
**Touches:** `docs/trace-schema.md`, `docs/task-definition-schema.md` (new)

## Context

The trace format is the data contract everything else depends on: the harness emits it, the scorer consumes it, audits read it. The task-definition format is its input-side dual: it tells the harness which `READ`/`QUIZ`/`RESET` events to run with what payloads. Locking both before code starts avoids painful migrations later.

Decision #1 (trace format) is locked to "JSONL event stream + per-`RESET` tarball snapshot, single run directory." This task fills in the structural details (exact fields, types, examples).

## Goal

Write `docs/trace-schema.md` and `docs/task-definition-schema.md` defining the two data contracts precisely enough that M2 (harness) and M6 (scorer) can be implemented against them without further discussion.

## Acceptance criteria

- [ ] `docs/trace-schema.md` exists and specifies:
  - Run directory layout (`trace.jsonl`, `snapshots/`, etc.)
  - JSONL event record schema: one record per event with `event_id`, `event_type` ∈ {`READ`, `QUIZ`, `RESET`}, `stage_meta`, `stage_input` (or pointer), `stage_output` (or pointer), `timing`, resource fields.
  - Per-`QUIZ` per-question record schema: `(question_id, probe_type ∈ {prior, ceiling, retention}, k, sut_answer, gold, question_type)` per decision #6's "harness emits a standardised per-question records file."
  - `question_seen_before` count field per decision #10 (option B: integer count of prior exposures).
  - `DIR` accounting fields per decision #8 (uncompressed bytes + file count + tar.gz size).
  - Resource appendix fields per decision #15: `(hardware_tier, declared_gpu, declared_train_flops, declared_inference_flops, wall_clock)`. For API SUTs: `(tokens_in, tokens_out, model_id, api_call_count)`.
  - Tarball-snapshot naming + provenance.
  - Worked example: a 3-event trace (PRIOR, READ, CEILING) rendered in full.
- [ ] `docs/task-definition-schema.md` exists and specifies:
  - File format (YAML or JSON — pick one; YAML preferred for readability).
  - Top-level fields: `task_id`, `description`, `events: [...]`, `questions: [...]`, `dir_policy` (per-task overrides if any).
  - Event entry schema: `event_type`, payload (text for `READ`, question references for `QUIZ`), `probe_type` + `k` for `QUIZ` events.
  - Question entry schema: `question_id`, `question_text`, `gold_answer`, `question_type` (surface/entity/multi-hop/thematic/retroactive), `material_ref` (which `READ` it depends on).
  - Worked example: the smoke-test shape (~5 questions, three probes each).

## Relevant files

- `docs/decisions-checklist.md` (#1, #6, #8, #10, #15) — the locked decisions this spec realises.
- `docs/tasks.md` — the book-track structure (`READ`/`QUIZ`/`RESET` semantics, probe definitions).
- `docs/metrics.md` — the `(R−P)/(C−P)` formula the scorer will compute from these records.
- `docs/protocol.md` — current `STAGE_INPUT`/`STAGE_OUTPUT` framing.

## Decisions already made

- JSONL events + tarball snapshots (decision #1A).
- Tagged-section `STAGE_INPUT` (`<TEXT>…</TEXT>`, `<QUESTIONS>…</QUESTIONS>`, `<META>…</META>`) per decision #2A. Task-definition format wraps the text payload; harness assembles tagged `STAGE_INPUT` from it.
- `C` definition: text-in-context + accumulated `QUIZ` history within the same process (decision #3A).
- Question exposure count is an integer (decision #10B).
- Both uncompressed bytes and tar.gz size reported (decision #8C).
- FLOPs reporting splits local (`train_flops`/`inference_flops`/`wall_clock`/`hardware_tier`) vs. API (`tokens_in`/`tokens_out`/`model_id`/`api_call_count`) per decision #15.

## Out of scope

- Implementation of writers or readers (M2/M6).
- LLM-judge scoring schema beyond exact-match (B3).
- Multi-SUT comparison / leaderboard rendering (post-MVP).
- Mock tool-call transcript schema for the in-context leaderboard (B5).
