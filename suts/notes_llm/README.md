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

## Two entrypoints: book-track vs. CL-Bench

Like the constructive SUT, this one speaks **two** wire contracts from one
codebase:

- **`python -m notes_llm`** — the original **book-track** `READ`/`QUIZ` event
  contract (above).
- **`python -m notes_llm.clbench_main`** — the **Continual Learning Bench**
  contract (`{prompt, response_schema, feedback}` → `{action, resource}`), driven
  through `retention_bench.SubprocessSystem`. This is the **in-context
  validation SUT**: the first retention-bench SUT meant to *lift the curve above
  the stateless prior* and show the gain-vs-`k` machinery measures a real curve.
  It is sourced from a capable API model — **not** the constructive research model
  (see `docs/constructive-sut-development-brief.md`).

  CL-Bench single-shot tasks have no separate READ stage, so per query the SUT
  (1) revises `DIR/notes.md` to capture the *persistent/latent structure* across
  all observations seen so far (the query `prompt` is the new observation), then
  (2) emits a JSON `action` conforming to the query's `response_schema`, derived
  only from the notes. Notes are flushed to `DIR` before the reply (surviving the
  `RESET` SIGKILL) and reloaded on a fresh spawn. A malformed model reply is
  coerced to a schema-minimal valid object, so the runner never crashes.

  **Retention mechanism (on `blind_spectrum_monitoring`):** a single scan shows
  only *currently-active* transmitters, but the report must cover the *persistent*
  occupied regions. Accumulated notes infer that persistent structure across
  scans; a hard `RESET` wipes the notes → back to the single-scan prior. That gap
  is the retention signal the curve measures.

### Producing the shaped curve (live; needs an API key)

```bash
OPENROUTER_API_KEY=… python -m retention_bench.gain_curve \
  --task blind_spectrum_monitoring \
  --task-kwarg variant=five_ch_wide --task-kwarg num_instances=6 \
  --sut "python -m notes_llm.clbench_main" \
  --extra-pythonpath suts/notes_llm \
  --reset-every 1 --reset-every 2 --name notes-llm
```

The goal is a band `C − P > 0` (ceiling above the stateless prior — **not**
`EXCLUDED`), the first non-degenerate retention curve. The plumbing is covered
offline (no key) by `tests/test_notes_clbench.py` against the fake-OpenAI shim.

## Install

```bash
cd suts/notes_llm
pip install -e .
```

In a shared/system Python (e.g. inside the dev container) this may require
`--break-system-packages`. The container image below is the reproducible
packaging path and avoids that workaround entirely.

## Container image (preferred packaging)

Extends the shared API base (`retention-bench/sut-python-base`, carrying the
`openai` SDK):

```bash
# Build the shared base once:
docker build -f suts/sut-python-base.Dockerfile \
  -t retention-bench/sut-python-base:0.1 suts/
# Then this SUT's image:
docker build -t retention-bench/sut-notes-llm:0.1 suts/notes_llm/
```

The harness launches a SUT in its image when the manifest declares an `image`
field; that wiring (plus the bare-host / dev-container smoke tests) lands in
a planned smoke-verification pass. See `docs/sut-interface.md` → "Launch modes".

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | (required) | API auth; SUT exits non-zero if absent. |
| `NOTES_LLM_MODEL` | `deepseek/deepseek-v4-flash` | Override model; `sut-manifest.json` records the default. |
| `RETENTION_BENCH_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible endpoint; override to point at another provider or a local proxy. |

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
