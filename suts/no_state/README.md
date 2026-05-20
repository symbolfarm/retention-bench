# no-state reference SUT

Floor row on the retention-bench leaderboard. Conforms to `docs/sut-interface.md`.

On `QUIZ` events the SUT calls the Anthropic API with the question text *only* —
no `DIR` reads, no in-memory accumulation, no priming from prior questions in
the same session. On `READ` events it returns an empty `stage_output`.

This is intentional: the no-state SUT measures the floor that any architecture
with actual retention must beat.

## Install

```bash
cd suts/no_state
pip install -e .
```

## Run standalone (smoke check, outside the harness)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
echo '{"event_id":"evt-0001","event_type":"QUIZ","stage_input":"<QUESTIONS><QUESTION id=\"q1\">What colour is the sky on a clear day?</QUESTION></QUESTIONS>"}' \
  | python -m no_state
```

Expected: a single line of JSON on stdout containing
`<ANSWER id="q1">…</ANSWER>` and token counts.

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | API auth; SUT exits non-zero if absent. |
| `NO_STATE_MODEL` | `claude-haiku-4-5-20251001` | Override model; `sut-manifest.json` records the default. |

## Manifest

See `sut-manifest.json`. Declares `mode=in-context`, `strict_verbatim=true`
(no-state has nothing to copy), `hardware_tier=API`.
