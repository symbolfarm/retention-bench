# Debrief: B9 Provider-neutral LLM calls via the OpenAI-compatible API

**Completed:** 2026-06-03
**Commits:** `6be9374` (source port), `c460bc8` (test-infra rework + green suite)

## What shipped

The four hardcoded `anthropic.Anthropic` call sites now construct
`openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url=…)` and call
`chat.completions.create`. OpenRouter is the default gateway; SUTs default to
`deepseek/deepseek-v4-flash`, the judge to a pinned `moonshotai/kimi-k2.6`.

- **3 text SUTs** (`no_state`, `notes_llm`, `naive_rag`) — client construction +
  response handling ported (system-as-message, `resp.choices[0].message.content`,
  `prompt_tokens`/`completion_tokens`). `DEFAULT_MODEL` + `DEFAULT_BASE_URL` constants;
  `RETENTION_BENCH_BASE_URL` override seam.
- **`scorer/judge.py`** — the riskiest piece: `_JUDGE_TOOL` rewrapped to OpenAI
  `{"type":"function","function":{…}}`, forced `tool_choice`, `_extract_tool_input`
  now `json.loads`es `message.tool_calls[*].function.arguments` (a JSON *string*,
  vs Anthropic's already-parsed `.input` dict). `rationale`-before-`score` field
  order preserved so the model still reasons before committing under a forced call.
- **Packaging** — `suts/sut-python-base.Dockerfile` + per-SUT Dockerfiles install
  `openai`; manifests' `env` lists and `model_id` defaults updated; `suts/*` and
  top-level `pyproject.toml` deps swapped (`no-state-sut` extra too).
- **Test infra** — the PYTHONPATH-shadowing fake-`anthropic` shim rebuilt as a
  fake `openai` shim (`tests/fake_openai_shim/openai.py`) presenting OpenAI response
  shape. YAML fixtures kept provider-neutral; the shim JSON-encodes tool `input`
  into the function-call `arguments` string. Env vars `FAKE_ANTHROPIC_*` →
  `FAKE_OPENAI_*`, `ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY`; test files / functions
  / fixtures renamed to drop "anthropic"; `model_id` assertions → deepseek.
- **`run.sh`** already sourced `.env` (from M7); only the comment needed updating.
- READMEs + scorer help text updated.

**74 passed, 3 skipped** (torch ×2 unrelated, live-key-gated integration ×1).

## Live verification

Driven end-to-end against real OpenRouter (`./run.sh smoke` path, key from `.env`):

- **SUT — `no_state` / deepseek:** resolved `deepseek/deepseek-v4-flash-20260423`,
  744 tokens in / 1147 out over 3 calls. Sensible answers on prior+ceiling probes,
  `not_found` on the post-RESET retention probe (the correct no-state floor).
- **Judge — kimi-k2.6:** `--scorer judge` on the same run made 4 live
  function-calling round-trips (`moonshotai/kimi-k2.6-20260420`, 1123 in / 1225
  out), returning structured verdicts + rationales. It correctly split q3
  (ceiling "policemen" ≈ "the police" → 1; prior "three policemen" dinged on
  specificity) — real semantic judgment through the new tool-call path.

Both call sites that exercise the new client are validated live; the packaging
half is validated by a real image build (`openai 2.40.0` imports, `anthropic`
absent in-image).

## Descoped / deferred

- **`NAIVE_RAG_EMBEDDER` seam** — left untouched by design (local dense retrieval,
  not a provider LLM call). Deliberate deviation from the original B9 backlog text.
- **Boundary token-counting proxy** — B9 only ensures the `base_url` override seam
  exists. Building the harness-owned counting proxy is a separate audit-fidelity
  task (see Follow-ups; sits near B10). Today the harness still trusts SUT
  self-report at `event_loop.py` accounting (verified unchanged).
- **Whether an open model judges as well as Claude** — separate measurement study;
  B9 just makes the judge model configurable + pinned.

## Design decisions

- **No new shared package.** Each component inlines ~3 lines of client construction
  so every Docker image stays build-self-contained. A shared helper would couple the
  images for no real gain.
- **YAML fixtures kept provider-neutral; shim does the shape translation.** The
  fixture stays `tool_use: {name, input}` + `input_tokens`/`output_tokens`; the shim
  maps it onto OpenAI shape (`json.dumps` the input into `arguments`,
  `prompt/completion_tokens` on `usage`). Zero fixture churn, and the fixture reads
  as "what response do we want" rather than "what does this SDK's wire format look like."
- **Renamed every provider-bearing identifier** (test files, functions, fixtures,
  env vars) rather than leaving `test_*_fake_anthropic.py` on openai-backed code.
  git mv makes it cheap and a stale name on a swapped dependency is a future trap.
  Kept the *contrastive* code comments ("Unlike Anthropic, arguments is a JSON
  string…") — those explain the port and stay useful.
- **`model_id` records the resolved dated snapshot.** OpenRouter resolves
  `deepseek/deepseek-v4-flash` → `…-20260423`; `response.model` threading captures
  it, so `resource_appendix.model_id` is the audit-true id, not the requested alias.

## Observations

- **The test-infra was the larger half of the task and the brief under-billed it.**
  The implementer-mode re-read called it "update any test stub referencing
  anthropic"; the reality was a whole fake-SDK scaffold (shim + 4 test files + 4
  fixtures + docker-launch + integration tests + help text), only surfaced by a
  repo-wide grep *after* the source port. Recorded as a process-memory: size the
  test-infra blast radius of an SDK/provider swap up front.
- **Stale `.env` override nearly hijacked the smoke.** `.env` still carried a pre-B9
  `NO_STATE_MODEL=claude-sonnet-4-6`; `run.sh`'s `set -a; . ./.env` would have
  pointed the SUT at a Claude id (which on OpenRouter needs an `anthropic/` prefix
  anyway). Unset it for the smoke to test the real deepseek default. Toby to remove
  the stale line (and the leftover `ANTHROPIC_API_KEY` / `DISABLED_API_KEY`).
- **Docker-in-docker came online during this task**, which is what made the
  image-build verification (and unblocking B4c) possible.

## Follow-ups

### Worth filing

- **Boundary token-counting proxy** — a harness-owned local proxy that forwards to
  OpenRouter via the `RETENTION_BENCH_BASE_URL` seam and tallies `usage` at the
  boundary, shifting token accounting from "trust SUT self-report" to "measured."
  Sits near B10.
- **Open-model judge quality validation** — does kimi-k2.6 agree with a Claude judge
  on a labelled set? The judge is a measuring instrument; its model choice deserves
  its own study before scores are treated as authoritative.
- **B4c is now unblocked** (docker-in-docker live) — harness image-launch wiring +
  smoke tests. A natural extension validates a containerized SUT against the
  fake-openai shim mounted via `RETENTION_BENCH_SHIM_DIR`.

### Drive-by

- `.gitignore` gained `.venv/` / `venv/` (a uv venv was created here to run pytest,
  since the dev container's system Python has no test deps and no pip).
