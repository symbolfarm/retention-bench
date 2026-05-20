# Debrief: M1 Trace + task-definition schemas

**Completed:** 2026-05-20
**Commit:** 2341cd3

## What shipped

Two new specs under `docs/`:

- `docs/trace-schema.md` — run-directory layout, `trace.jsonl` event records (READ/QUIZ/RESET with per-type fields), `questions.jsonl` per-(question, probe) records, `run-manifest.json`, `sut-manifest.json` (with the local-vs-API resource-appendix split from #15). Stage payloads (`stages/<event_id>.in/.out`) referenced by path from the trace rather than inlined, so the JSONL stays small and greppable even when `READ` events carry chapter-length text. Worked example: 3-event prior→read→ceiling trace rendered in full across `trace.jsonl`, `questions.jsonl`, and stage payloads.

- `docs/task-definition-schema.md` — YAML format, top-level `materials` / `questions` / `events` sections, per-event-type fields (`quiz` with `probe`+`k`, `read` with `material_id`, `reset` payload-less), validation rules (probe-placement vs. READ/RESET ordering, ID uniqueness, exactly-one-of `path`/`text` for materials). Worked example: full smoke-test shape (5 questions × 3 probes, one RESET).

Realises decisions #1, #2, #6, #8, #10, #15.

## Descoped / deferred

- Inline LLM-judge gold answer schema — gold is a plain string for MVP (exact-match scorer in M6); richer gold schemas land with B3.
- Multi-author rotation per #5A is recorded in `decisions-checklist.md` but doesn't need a schema slot until cohort-1 dispatch (B8).
- `protocol.md` rewrite — flagged: parts of this spec supersede protocol.md statements. Left for B7 / a wider protocol-rewrite pass.

## Design decisions

- **Stage payloads pointed-to, not inlined.** `trace.jsonl` carries paths to `stages/<event_id>.{in,out}`; the actual STAGE_INPUT/STAGE_OUTPUT text lives on disk separately. Reason: a chapter-length `READ` event would otherwise blow out the trace file. The trace stays grep-friendly; per-event audit just reads the pointed-to file. Reversible — could inline short payloads later if anyone cares.

- **Split `questions.jsonl` from `trace.jsonl`.** Decision #6 calls for "a per-`QUIZ` records file" the scorer reads. I made this a separate JSONL rather than per-question fields embedded in QUIZ event records. The scorer never has to walk `trace.jsonl` at all — keeps the swap-the-scorer-out invariant clean.

- **`question_seen_before` as count, not boolean.** Decision #10 is locked to option B (integer count) — implemented straight; just noting it's load-bearing for any post-hoc analysis that needs to ask "did the SUT get this question fresh or had it seen it before?"

- **`<ANSWER id="q1">…</ANSWER>` parsing convention for SUT QUIZ output.** Not pre-specified; I picked it as the natural dual of the `<QUESTION id="q1">…</QUESTION>` tagged-section format from #2A. `parsing_status` field on per-question records surfaces parse failures (`not_found`, `ambiguous`) without crashing the run. M3 needs to implement this convention on the SUT side and the harness needs to parse it.

- **`<META>` block delivered to the SUT, not just internal trace metadata.** Carries `type`, `probe`, `event_id`. Useful for SUTs that want to behave differently per event type (e.g., a notes-LLM might skip note-writing on QUIZ events). Costs little.

- **`run_id` format = `<task_id>-<iso8601>-<short-hash>`.** Sortable, traceable, no DB needed.

- **YAML over JSON for task definitions.** Multi-line text and inline comments matter for question/material authoring; the harness loads via stdlib equivalent (PyYAML in M2). For trace output, JSONL is right — machine-emitted, append-only.

- **Validation rule that the harness refuses to run ill-formed tasks** (rather than warning and proceeding). Cheap; catches probe-placement bugs early; aligns with "trust the contract" elsewhere in the design.

## Observations

- The trace schema is doing dual duty: data format AND the SUT-side answer-format convention (`<ANSWER>` tags). M3 will need to know both. I cross-referenced explicitly in trace-schema.md and called it out in M3's existing task brief — but worth flagging to anyone picking up M2/M3 that the contract spans both docs.

- The decisions checklist resolved enough fields that very little judgement was needed for the schema content itself. The judgement went into structural choices (split files vs. one big file; pointed-to payloads vs. inline). That's a healthy ratio — means M2/M3 won't be re-litigating settled decisions.

- The smoke-test material I chose for the worked example (*The Metamorphosis*) is exactly the public-domain text M5 is likely to pick. Convenient; if M5 picks something else, the example here is still illustrative.

- No code was written, no harness behaviour to verify. Pure spec work. The first real "does this hang together?" test will be M4 (end-to-end integration), where any schema seam shows up.

## Follow-ups

### Filed as tasks

(None — M2/M3/M5/M6 are already filed and now unblocked.)

### Drive-by cleanup landed

- None.

### Considered and dropped

- **JSON Schema validation files for trace + task-def.** Tempting (gives M2/M3 free validators) but premature: the schemas are still likely to shift slightly during M2/M3 implementation as edge cases surface. Lock them after M4 lands, when the contracts have survived one real round-trip. Tracking informally; no task file.
- **`protocol.md` rewrite as a M1 sub-task.** Mentioned the supersession in trace-schema.md cross-references but did not patch protocol.md inline — it would have ballooned this task. Stays as B7.
