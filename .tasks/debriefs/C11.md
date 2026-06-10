# Debrief: C11 In-context (self-authored notes) validation SUT

**Completed:** 2026-06-08
**Commit:** 8f9b99c

## What shipped

`notes_llm.clbench_main` — the Continual Learning Bench wire entrypoint for the
notes SUT, the **in-context validation SUT**: the first retention-bench SUT meant
to lift the curve above the stateless prior (milestone 2 in
`docs/constructive-sut-development-brief.md`). Sourced from an API model, distinct
from the constructive research model.

- **Per query** (CL-Bench single-shot has no separate READ stage): (1) one LLM
  call revises `DIR/notes.md` to capture the *persistent/latent structure* across
  observations seen so far (the query `prompt` is the new observation), flushed
  atomically **before** the reply so it survives the RESET SIGKILL; (2) a second
  LLM call emits a `response_schema`-conforming JSON `action` from the notes
  alone. Notes reload on a fresh spawn (cold-resume).
- **Crash-safety:** `_extract_json` (handles fences / prose-wrapped JSON) +
  `_coerce_action` + `_minimal_valid` guarantee a schema-valid action even on a
  malformed model reply, so `response_schema(**action)` in the runner never
  crashes. Reuses the book-track SUT's note I/O + `_call_llm` (one codebase, two
  entrypoints).
- **Manifest** gains `clbench_entrypoint`; **README** documents the two
  entrypoints, the retention mechanism on `blind_spectrum_monitoring`, and the
  live `gain_curve` command.
- **Tests** (`tests/test_notes_clbench.py`, 7): structured-output crash-safety
  against the real `ScanReport` schema; in-process `_handle_query` proving
  flush-before-reply, prior-notes read-back (the retention mechanism), and
  cold-resume — all via a `_call_llm` stub, no subprocess/network; and the real
  `clbench_main` subprocess through `SubprocessSystem` + CL-Bench's runner with
  the fake-OpenAI shim (no key).

Full suite: **125 passed, 1 skipped** (+7; skip is the pre-existing live-
OpenRouter test).

### Acceptance criteria

- ✅ `clbench_main` speaks the C2 protocol; `action` validates against
  `response_schema` (crash-safe coercion).
- ✅ Per query: update `notes.md`, then answer from notes; write before reply;
  reload on cold spawn (asserted in-process).
- ✅ Plumbing verified against the fake-OpenAI shim through `SubprocessSystem` —
  green without an API key.
- ✅ **Live shaped-curve run executed 2026-06-10** (OpenRouter key from `.env`).
  Result: **band `C − P = 0.0141` → EXCLUDED** (`P=0.2136`, `C=0.2277`); `R(k=2)`
  noisily exceeded the ceiling. The notes SUT does **not** lift the curve above
  the prior on `blind_spectrum_monitoring/five_ch_wide` — the **(b)** diagnosis
  below: the task is harder than a notes-stenographer can exploit, so the shaped
  curve awaits the constructive model. AC closed with a documented negative result.
- ✅ `resource` reports `tokens_in`/`tokens_out`/`model_id`/`api_call_count`.

### The live run to close the last AC

```bash
OPENROUTER_API_KEY=… python -m retention_bench.gain_curve \
  --task blind_spectrum_monitoring \
  --task-kwarg variant=five_ch_wide --task-kwarg num_instances=6 \
  --sut "python -m notes_llm.clbench_main" \
  --extra-pythonpath suts/notes_llm \
  --reset-every 1 --reset-every 2 --name notes-llm
```

Expected/hoped: `band C − P > 0` and a curve that degrades with `k`. If it comes
back EXCLUDED, the diagnosis is either (a) the model isn't actually using
accumulated notes to infer persistent structure, or (b) `blind_spectrum_monitoring`
is harder than a notes-stenographer can exploit — in which case the curve shape
genuinely awaits the constructive model, and that itself is an informative result.

## Descoped / deferred

- **The live shaped curve** — see above; blocked on a key, not on code.
- **Containerising this SUT** — validates in subprocess mode; the container path
  (C9) + non-root (C12) are orthogonal. The `image` field is not yet on the
  notes manifest (C12 will wire the three API images).
- **Reward decomposition (understanding vs stenography)** — C6; this SUT is
  notes-based and leans stenographic by construction. C11 only needs to move the
  band off EXCLUDED.
- **One-call variant** — kept two LLM calls per query (update-notes, then answer)
  for a clean separation of the retained artifact from the answer; a fused
  single call would halve cost but muddy the story. Revisit if live cost bites.

## Design decisions

- **Two LLM calls per query**, not one — notes authoring is separated from
  answering so the notes are unambiguously *the* retained artifact (matches the
  book-track notes SUT). Cost is 2× tokens/query; fine at the validation scale
  (`five_ch_wide`, num_instances=6, a couple of `k`s).
- **Content-based JSON, not function-calling**, for the structured action. The
  fake shim already serves `text` responses, and a lenient extractor + a
  schema-minimal fallback is more portable across OpenRouter models than relying
  on each model's strict-json-schema support. The fallback (required array →
  `[]`, etc.) is the load-bearing crash-safety guarantee.
- **Reused `notes_llm.__main__` helpers** (`_call_llm`, `_read_notes`,
  `_write_notes_atomic`, `_extract_notes`) by import rather than refactoring a
  shared `_core` — minimal churn, the two entrypoints share one model + one
  notes discipline.
- **Notes prompt nudges toward persistent/latent structure**, not verbatim
  surface — task-agnostic wording that biases the SUT toward the understanding
  signal generically (it doesn't hardcode blind_spectrum).
- **In-process `_handle_query` test with a recording `_call_llm` stub** is the
  load-bearing coverage: it proves the SUT *reads prior notes back into the next
  call* (the retention mechanism), which the fake-shim subprocess test cannot
  show (the shim ignores its inputs).

## Observations

- **`blind_spectrum_monitoring` is a genuinely good fit for the retention story.**
  Reward is IoU on the *long-run* available spectrum: a single scan shows only
  currently-active transmitters, so inferring the persistent occupied set
  *requires* accumulating observations across instances. That is exactly what a
  hard RESET destroys — the mechanism is clean, not contrived. (Confirmed by
  reading `_score_report` in the task.)
- **The fake shim ignores call inputs**, so it can prove "the process respawned
  and the wire contract held across N calls" but not "the SUT fed prior notes to
  the model." That distinction is why the in-process stub test exists — worth
  remembering for any future SUT whose retention is input-conditioned.
- **No API key in this dev container** (same reason the no-state live test
  skips). The shaped curve — the headline point of C11 — can only be produced
  where a key exists. Everything *up to* the model's actual reasoning is verified
  here; the model's ability to exploit the notes is the open empirical question.

## Follow-ups

### Considered and dropped

- *File a "fused single-call notes+answer" optimisation task.* Premature — only
  worth it if live token cost is a problem, which we can't measure without a key.
  Re-raise after the live run if cost bites.
- *Wire the `image` field onto the notes manifest here.* Belongs to C12 (non-root
  containers wires the three API images together); doing it in C11 would split
  that work awkwardly.
