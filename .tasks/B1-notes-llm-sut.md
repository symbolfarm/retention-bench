# B1 Notes-LLM reference SUT

**Priority:** medium
**Blocked by:** nothing (B10 landed; harness path is regression-protected)
**Touches:** `suts/notes_llm/`, `tests/fixtures/`, `tests/test_notes_llm_*.py`

## Context

B1 is the second reference SUT. Where no-state has no DIR usage (floor of
retention curve), notes-LLM is the first SUT to *use* `DIR` for cross-RESET
persistence. It is also the first SUT to produce a non-flat retention
curve, which makes it a load-bearing artifact: per
[[project_cleval_dual_purpose]], sample outputs from B1 may end up in
outward-facing material, so we want it to be a fair representative of
what notes-LLM-style SUTs can do — not a strawman.

The design space was scoped jointly with Toby on 2026-05-20 before any
code was written. See "Decisions already made" below.

## Goal

A runnable reference SUT under `suts/notes_llm/` that takes notes to
`DIR/notes.md` during READ events and answers from those notes during
QUIZ events. Same packaging shape as `suts/no_state/`. Drives end-to-end
through the harness, produces a non-flat retention curve on a
multi-chapter task fixture.

## Acceptance criteria

- [ ] `suts/notes_llm/` package with `sut-manifest.json`,
      `notes_llm/__main__.py`, `pyproject.toml`, `README.md`.
- [ ] On READ: SUT reads `DIR/notes.md` (if exists), makes one LLM call
      with system + chapter + prior notes, parses `<NOTES>…</NOTES>`
      from response, writes the result to `DIR/notes.md`.
- [ ] On QUIZ: SUT reads `DIR/notes.md`, makes one LLM call with
      system + notes + question(s), parses `<ANSWER>` tags, returns
      structured `answers` list per docs/sut-interface.md.
- [ ] Resource fields (`tokens_in`, `tokens_out`, `api_call_count`,
      `model_id`) emitted on every LLM-using event reply.
- [ ] Multi-chapter test fixture (e.g. `tests/fixtures/two_chapter.yaml`)
      exercising the cumulative-notes path across at least 2 READs and
      1 RESET.
- [ ] Integration test against the fake-anthropic shim (extend B10
      pattern) covering: notes written to DIR after READ, notes survive
      RESET, QUIZ answers are extracted from the notes-based reply.
- [ ] All existing tests still pass.

## Decisions already made (joint scoping, 2026-05-20)

- **Notes shape:** single freeform `DIR/notes.md` file. SUT chooses
  format (bullets, prose, Q&A) — we measure outcomes, not form.
- **Write phase:** READ only. Notes are write-once-per-chapter during
  READ; read-only during QUIZ. Frames notes as a reading strategy, not
  an answering strategy.
- **READ context:** chapter text + own existing notes. No question
  pre-roll (no upcoming-question leakage). Pure reading-strategy
  baseline.
- **QUIZ context:** question + own notes.md only. No chapter text, no
  prior QUIZ history. Pure retention test.
- **Notes evolution:** cumulative. On READ #N, SUT sees prior notes
  and writes a new full file (which may revise/extend). `notes.md`
  is the union of what it chose to keep across all chapters so far.
- **Write call:** single `messages.create()` per READ. Model emits
  new notes content inside `<NOTES>…</NOTES>` tags; SUT parses and
  writes. Same harness-side pattern as no-state's `<ANSWER>` tags.
- **Model:** same as no-state — Haiku 4.5 default, `NOTES_LLM_MODEL`
  env var override. Same model for reading and answering, so the
  retention curve isolates the value of notes (not model swap).
- **Size budget:** no hard cap. Advisory limit (~2000 tokens) in the
  system prompt. Trace records final notes size; if SUTs blow past
  the advisory, that's a finding.
- **Mode:** `in-context` (not `agentic`). Notes live in DIR but the
  SUT is not running an agent loop.

## Relevant files

- `suts/no_state/no_state/__main__.py` — template for the SUT shape.
- `suts/no_state/sut-manifest.json` — template manifest.
- `docs/sut-interface.md` — wire contract.
- `tests/fake_anthropic_shim/anthropic.py` — for tests.
- `tests/test_no_state_fake_anthropic.py` — pattern for the new test.
- `tests/fixtures/trivial.yaml` — base fixture; clone & extend.

## Out of scope

- Naive-RAG (B2) — separate SUT, vector index in DIR.
- LLM-judge scorer (B3) — exact-match remains for now.
- Tool-use / agentic notes loop — explicitly deferred (decided above).
- Per-call model configuration via manifest — explicitly deferred.
- Hard notes budget enforcement — explicitly deferred.
- Generic LLM-backend abstraction (B9).
