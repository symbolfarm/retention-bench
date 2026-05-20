# Tasks

> **Agents:** read this file at the start of every session, then consult
> `.tasks/LOG.jsonl` for the current task queue. The `task-cycle` skill
> (in `~/.claude/skills/task-cycle/SKILL.md`) describes how to start and complete
> tasks. Use `~/.claude/skills/task-cycle/assets/task-template.md` when creating
> new task files.

## Current focus

**Operational MVP for the book-track.** Goal: a runnable end-to-end smoke test
where the harness drives a no-state reference SUT through a toy book-track task,
produces a trace, scores it, and renders a retention curve. No cohort-1 assets,
no LLM-judge scoring, no container packaging — just the smallest thing that
exercises the full pipeline.

Definition of done for MVP: `./run.sh smoke-test` produces a JSONL trace and a
printed `P`/`C`/`R(k)` retention curve, end-to-end, on the no-state SUT.

**Stack (decided 2026-05-20):** Python for harness + reference SUTs. Anthropic
SDK for the no-state SUT's LLM calls. Rust port of the harness is a possible
post-MVP learning exercise; the SUT contract is process-level so cross-language
ports are free once the contract is stable.

## MVP task list (proposed — not yet filed)

Tasks numbered M1–M7 are the candidate MVP build order. They will be filed as
individual `.tasks/M*.md` task files after a debrief pass.

1. **M1 — Trace schema spec.** Write `docs/trace-schema.md` defining the JSONL
   event stream format and per-`QUIZ` record schema. Resolves the structural
   details deferred from decision #1. Pure spec; no code.
2. **M2 — Harness skeleton (event loop + DIR lifecycle).** Read a task
   definition, run the `READ`/`QUIZ`/`RESET` loop, manage subprocess and `DIR`
   (incl. tar.gz + bytes-on-disk snapshotting per #8), emit trace. Stub SUT for
   testing.
3. **M3 — SUT interface spec + no-state reference SUT.** Small spec for the SUT
   binary contract (stdin/stdout vs. files). Implement the no-state baseline:
   call an LLM API with `STAGE_INPUT`, return response, ignore `DIR`.
4. **M4 — Wire harness + no-state SUT end-to-end.** First integration; harness
   actually drives a real SUT through a trivial task definition.
5. **M5 — Smoke-test task definition.** Short placeholder text (~1–2 pages) +
   ~5 questions, three probes per question. Explicitly labelled smoke-test, not
   cohort-1.
6. **M6 — Exact-match scorer + retention-curve renderer.** Pure function over
   the trace, emits `P`, `C`, `R(k)` per question and aggregate curve. Per
   decision #6, exact-match is enough for MVP; LLM-judge integration is
   post-MVP.
7. **M7 — End-to-end smoke run.** Execute M5 via M2 + M3, score with M6,
   produce curve. The "operational MVP" milestone.

## Backlog (post-MVP, not yet ordered)

- B1 — notes-LLM reference SUT (decision #11).
- B2 — naive-RAG reference SUT (decision #11).
- B3 — LLM-as-judge scorer integration via DeepEval or Inspect (decision #6).
- B4 — Docker container packaging + tier-declaration scaffolding (decision #16).
- B5 — Mock tool-call transcript authorship strategy + first in-context-leaderboard variant (decision #7 deferred sub-decision).
- B6 — `docs/interface.md` rewrite to match Turn 3 five-thing contract + two-leaderboard resolution.
- B7 — `docs/metrics.md` write-in: resolved `C` definition (text-in-context + accumulated `QUIZ` history) + storage-delta-= 0 rule for in-place training + FLOPs reporting fields.
- B8 — Cohort-1 novella dispatch (blocked on Toby's sign-off; orthogonal to harness MVP).

## Structure

```
.tasks/
├── LOG.jsonl              # Append-only audit log of all tasks
├── debriefs/              # One debrief file per completed task
│   └── M1-....md
├── M2-....md              # Pending/active task files (deleted on completion)
└── M3-....md
```

## Quick reference

| What | Where |
|---|---|
| Full task queue | `.tasks/LOG.jsonl` |
| Active task files | `.tasks/*.md` |
| Completed debriefs | `.tasks/debriefs/` |
| Task template | `~/.claude/skills/task-cycle/assets/task-template.md` |
| Debrief template | `~/.claude/skills/task-cycle/assets/debrief-template.md` |
| Skill instructions | `~/.claude/skills/task-cycle/SKILL.md` |
