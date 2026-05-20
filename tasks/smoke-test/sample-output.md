# Smoke-test sample output

Captured 2026-05-20 from a fresh `./run.sh smoke` against the no-state
reference SUT (`claude-sonnet-4-6` via Anthropic API). Run ID:
`smoke-test-2026-05-20T06-52-26Z-e0a6ec`.

Sonnet was used instead of the manifest-default Haiku 4.5 because
Haiku was returning persistent `529 Overloaded` at run time; the model
is configurable via the `NO_STATE_MODEL` env var. Run shape is
identical either way.

## Scorer output (terminal)

```
question_id | P | C | R(1) | norm_R(1)
q1 | 0.00 | 0.00 | 0.00 | (excluded — C≈P)
q2 | 1.00 | 1.00 | 1.00 | (excluded — C≈P)
q3 | 0.00 | 0.00 | 0.00 | (excluded — C≈P)
q4 | 0.00 | 0.00 | 0.00 | (excluded — C≈P)
q5 | 1.00 | 1.00 | 1.00 | (excluded — C≈P)

aggregate: (no usable questions — all excluded or no retention probes)
```

**This is the correct floor-SUT result.** The no-state SUT never sees
the source text — `READ` is a no-op for it. So `C` (post-read ceiling)
necessarily equals `P` (pre-read prior), and every question is
excluded by the `C≈P` rule. The aggregate is empty by design.

What this tells us:

- **The pipeline runs end-to-end.** Harness drove the SUT through
  5 events (`prior → read → ceiling → reset → retention@1`), wrote a
  well-formed trace, and the scorer parsed it cleanly.
- **The `C≈P` exclusion rule fires correctly.** The smoke test is a
  scorer-correctness smoke as well as a wiring smoke.
- **Saturated questions (q2 "seven", q5 "eighth") score 1.0 across
  all probes**, because Sonnet 4.6 knows the Tell-Tale Heart well
  enough to answer the single-word golds from pretraining alone.
- **Verbose-answer questions (q1, q3, q4) score 0.0**, because the
  model answers correctly but with extra detail
  (e.g. `"Pale blue (with a film/veil over it)"` for gold `"pale
  blue"`). Exact-match scoring is fragile against LLM verbosity by
  design — the LLM-judge integration (backlog B3) will address this
  post-MVP.

## Per-question answers (one example, prior probe)

| qid | type | gold | sut_answer |
|---|---|---|---|
| q1 | surface_factual | `pale blue` | `Pale blue (with a film/veil over it)` |
| q2 | surface_factual | `seven` | `Seven` |
| q3 | entity_tracking | `the police` | `Three police officers (policemen)` |
| q4 | surface_factual | `a heartbeat` | `The beating of the old man's heart` |
| q5 | multi_hop | `eighth` | `Eighth` |

Specific `sut_answer` strings are not reproducible — LLM responses
vary across runs. Run **shape** (event count, question count, probe
types, exclusion behaviour) is reproducible.

## Resource appendix (from `sut-manifest.json`)

```json
{
  "resource_appendix": {
    "kind": "api",
    "model_id": "claude-sonnet-4-6",
    "tokens_in": 825,
    "tokens_out": 376,
    "api_call_count": 3,
    "wall_clock_ms": 11275
  }
}
```

3 API calls (one per `QUIZ`; `READ` is a no-op for no-state). At
Sonnet 4.6 list prices, the run cost was approximately $0.008 USD.

## Run-manifest summary

```json
{
  "task_id": "smoke-test",
  "event_count": 5,
  "reset_count": 1,
  "sut_invocation_count": 2,
  "exit_status": "ok"
}
```

5 events (3 QUIZ, 1 READ, 1 RESET). 2 SUT process spawns (initial +
post-RESET respawn).
