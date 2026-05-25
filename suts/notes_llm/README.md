# notes-LLM reference SUT

Second reference SUT for retention-bench. First SUT to use `DIR` for
cross-`RESET` persistence, and the first expected to produce a non-flat
retention curve. Conforms to `docs/sut-interface.md`.

## Behaviour

- **READ:** reads `DIR/notes.md` (if present), then asks the LLM to produce a
  revised, cumulative notes file given the current chapter + existing notes.
  The model wraps its output in `<NOTES>…</NOTES>`; the SUT parses the tags
  and rewrites `DIR/notes.md` atomically.
- **QUIZ:** reads `DIR/notes.md`, asks the LLM to answer the questions given
  only the notes (no chapter text, no prior QUIZ history). The model wraps
  per-question answers in `<ANSWER id="…">…</ANSWER>` tags, which the SUT
  parses into the structured `answers` list the harness expects.

Notes are cumulative: each READ shows the model its prior notes and asks it
to produce the next full version. The model decides format (bullets, prose,
Q&A), what to keep, and what to drop. We measure outcomes, not form.

This is the "in-context" tier: notes live in `DIR`, but the SUT is not
running an agent loop.

## Install

```bash
cd suts/notes_llm
pip install -e .
```

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | API auth; SUT exits non-zero if absent. |
| `NOTES_LLM_MODEL` | `claude-haiku-4-5-20251001` | Override model; `sut-manifest.json` records the default. |

Same model used for both READ (note-taking) and QUIZ (answering), so the
retention curve isolates the value of notes rather than a model swap.

## Notes size

There is no hard cap. The system prompt advises ~2000 tokens. If a SUT blows
past that, the resulting trace records the actual file size and that's a
finding.

## Manifest

See `sut-manifest.json`. Declares `mode=in-context`, `strict_verbatim=false`
(notes may contain verbatim spans from the source — that's the SUT's choice,
and is now an auditable property of `DIR/notes.md`).
