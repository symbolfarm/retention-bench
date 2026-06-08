# C11 In-context (self-authored notes) validation SUT — give the curve shape

**Priority:** high
**Blocked by:** nothing (C2/C4 done; notes_llm SUT exists from B1)
**Touches:** `suts/notes_llm/`, `tests/`, `docs/metrics.md`

## Context

Every retention curve today reports `band EXCLUDED` because no SUT benefits from
retained state — the only stateful SUT (constructive, C3) emits gibberish. This
task delivers the **first SUT that lifts the ceiling above the stateless prior**
(milestone 2 in `docs/constructive-sut-development-brief.md`), proving the
gain-vs-`k` machinery measures a real curve. It is a *benchmark-validation*
artifact, sourced from a capable API model — explicitly **not** the constructive
research model (that lives in its own project; see the dev brief).

Decided with Toby (2026-06-08):
- **Memory mechanism: self-authored notes.** Per query the model (a) updates a
  running `notes.md` in DIR from the instance's observation content, then (b)
  answers the current query conditioned on the accumulated notes. Understanding-
  leaning: the model *compresses* what it has seen rather than storing verbatim.
- **Backend: API via OpenRouter** (the B9 OpenAI-compatible path; deepseek
  default). Needs `OPENROUTER_API_KEY` for a live shaped-curve run — absent in
  the dev container, so plumbing is tested against the fake-OpenAI shim here and
  the actual shaped curve is produced where a key exists.

## Goal

A CL-Bench-path entrypoint for the notes SUT (mirroring
`constructive.clbench_main`) that retains via self-authored notes in DIR and, run
through `retention_bench.gain_curve` on `blind_spectrum_monitoring`, produces a
**non-EXCLUDED** band (`C > P`) and a retention curve with shape.

## How retention works here (single-shot)

`blind_spectrum_monitoring` is single-shot (one `respond()` per instance, no
`feedback`). Each instance's **prompt carries observation content**; the model
accumulates structure from the stream of prompts it has seen (unsupervised
episodic→understanding), improving the current answer. A hard RESET wipes the
notes → back to prior. Confirm the prompt actually carries learnable content when
implementing (it does for the constructive SUT, which trains on prompt bytes).

## Acceptance criteria

- [ ] A `clbench_main`-style entrypoint on the notes SUT speaks the C2 wire
      protocol (`{prompt, response_schema, feedback}` → `{action, resource}`),
      with `action` validating against `response_schema`.
- [ ] Per query: update `notes.md` in DIR from the prompt, then answer
      conditioned on notes; **write notes before replying** (survives SIGKILL);
      reload notes on cold spawn.
- [ ] Plumbing verified against the fake-OpenAI shim through `SubprocessSystem`
      (canned responses; asserts notes persist across a hard reset and restart
      in the wiped arm) — green without an API key.
- [ ] Documented live run: with `OPENROUTER_API_KEY`, `gain_curve` on
      `blind_spectrum_monitoring` yields `C > P` (band **not** EXCLUDED) and a
      rendered curve. Capture the curve in the debrief.
- [ ] `resource` reports tokens (`tokens_in`/`tokens_out`/`model_id`) so the
      compute channel is populated.

## Relevant files

- `suts/notes_llm/` — existing notes SUT (B1, book-track READ/QUIZ); add the
  CL-Bench entrypoint alongside, reusing its note-writing logic. Model on
  `suts/constructive/constructive/clbench_main.py` (the two-entrypoint pattern).
- `retention_bench/gain_curve.py` — the validation driver (no changes expected).
- `tests/fake_openai_shim/`, `tests/test_notes_llm_fake_openai.py` — the
  shim-based plumbing test pattern to mirror.
- `docs/metrics.md` — note the first non-EXCLUDED curve once it exists.

## Decisions already made

- Self-authored notes (not RAG / not full-transcript); API backend (not local) —
  see Context.
- Validate in **subprocess mode**; containerisation is orthogonal (C9/C12).

## Out of scope

- The constructive research model (separate project; `docs/constructive-sut-
  development-brief.md`).
- The reward decomposition that separates understanding from stenography (C6).
- Containerising this SUT.
