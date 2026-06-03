# B9 Provider-neutral LLM calls via the OpenAI-compatible API

**Priority:** medium
**Blocked by:** nothing
**Touches:** `suts/no_state/no_state/__main__.py`, `suts/notes_llm/notes_llm/__main__.py`, `suts/naive_rag/naive_rag/__main__.py`, `scorer/judge.py`, `suts/*/sut-manifest.json`, `suts/*/pyproject.toml`, `suts/*/Dockerfile`, `pyproject.toml`, `README.md`, `tests/*`

## Context

Four call sites currently hardcode `anthropic.Anthropic(...)` against closed-weights
Claude models: the three text SUTs (`no_state`, `notes_llm`, `naive_rag`) and the
LLM-as-judge scorer (`scorer/judge.py`). The original B9 backlog framed this as
"collapse 4 copies into 1 uniform provider abstraction."

**This brief is a rescope (decided 2026-06-03 with Toby).** Stepping back from
"abstract everything," the motivation analysis split the four sites by what they
actually need:

- **SUTs are reference baselines.** They don't need a general multi-provider
  framework — they need the *right default*. Hardcoding closed-weights Anthropic
  contradicts Toby's stated preference for low-cost open models. The fix is to
  point them at an **OpenAI-compatible endpoint** (the open-model ecosystem has
  standardised on the OpenAI API), defaulting to an open model.
- **The judge is a measuring instrument.** Generality there is low-value and
  mildly hazardous — you want one strong model *pinned* so retention scores stay
  comparable across runs. It also leans on tool-use/structured output, the part
  open models are flakiest at, so it gets a frontier open model, not the cheap
  SUT default.
- **Synthetic data generation** is where multi-model *variety* genuinely pays
  (asset diversity for benchmark validity + token cost). But **no synth-gen code
  exists yet** (only planning docs), so B9 builds nothing for it — just leaves a
  clean, reusable client idiom for it to adopt later (B5/B8).

The "lucky convergence": OpenRouter (an OpenAI-compatible gateway) fronts many
open models behind one integration, so "use cheap open models now" and "support
model variety for synth-gen later" are the same lever.

## Goal

Replace the hardcoded Anthropic SDK at the three text SUTs and the judge with the
`openai` SDK pointed at an OpenAI-compatible `base_url` (OpenRouter), defaulting
the SUTs to a low-cost open model and the judge to a frontier open model. No new
shared package — inline the ~3-line client construction per component so each
Docker image stays self-contained. Verify at least one SUT end-to-end against a
real OpenRouter call.

## Decisions already made

- **Transport:** the official `openai` SDK (MIT, thin, the de-facto client for
  OpenAI-compatible endpoints). Not LiteLLM/pydantic-ai (heavy dep in every image),
  not hand-rolled HTTP. Consistent with B3/decision #6, which was about not pulling
  a *scoring* library — not about HTTP plumbing.
- **Gateway / base_url:** OpenRouter, `https://openrouter.ai/api/v1`. One
  integration serves the SUTs now and synth-gen variety later; can still pin
  DeepSeek-family models through it.
- **Default models:**
  - SUTs → `deepseek/deepseek-v4-flash` (cheap; they're reference rows).
  - Judge → `moonshotai/kimi-k2.6` (frontier open; reliable tool-use matters here).
- **No new package.** Inline the client construction + response handling per
  component (or a vendored micro-helper at most). Keeps each SUT image
  build-self-contained; ~3 trivial lines drifting is a non-problem.
- **Env-var contract:**
  - `OPENROUTER_API_KEY` — shared key, all four sites (replaces `ANTHROPIC_API_KEY`).
    Toby will drop it in a `.env` in the workspace root. **Never read its value
    into tool output — reference it by name only.**
  - `base_url` defaults to the OpenRouter URL via a module constant, overridable
    by an optional `RETENTION_BENCH_BASE_URL` env var (this override is the seam
    that a future boundary-counting proxy — see Out of scope — will use).
  - Per-role model vars stay as-is in name (`NO_STATE_MODEL`, `NOTES_LLM_MODEL`,
    `NAIVE_RAG_MODEL`, `RETENTION_BENCH_JUDGE_MODEL`), only their defaults change.
- **`.env` loading (caught on re-read).** SUTs/judge read `os.environ`; a `.env`
  in the workspace root is **not** auto-sourced. The harness forwards its own env
  to SUT subprocesses, so the *harness process* must have `OPENROUTER_API_KEY` set
  before launch. Make `run.sh` source `.env` if present (`set -a; . ./.env; set +a`)
  so the live path works without the operator exporting by hand. Do **not** add
  `python-dotenv` as a dependency — keep loading in the shell entrypoint, not baked
  into every SUT image.
- **Keep `max_tokens` (caught on re-read).** OpenRouter accepts the `max_tokens`
  kwarg; no need to migrate to `max_completion_tokens`. Leave the existing
  `max_tokens=MAX_TOKENS` calls as-is apart from the method rename.
- **OpenRouter attribution headers are optional (caught on re-read).** `HTTP-Referer`
  / `X-Title` (via the `openai` SDK's `default_headers`) only affect OpenRouter's
  public rankings; not needed for function. Skip unless desired.
- **Judge model stays pinned, not varied.** Treat `RETENTION_BENCH_JUDGE_MODEL`
  as a recorded measurement parameter. Whether an open model judges *as well as*
  Claude is a separate validation, not assumed here.

## Anthropic → OpenAI API shape changes (the real work)

Per call, the SDK surfaces differ — these are the gotchas:

| Concern | Anthropic (current) | OpenAI-compatible (target) |
|---|---|---|
| Method | `client.messages.create(...)` | `client.chat.completions.create(...)` |
| System prompt | `system=` kwarg | a `{"role":"system",...}` message at the front of `messages` |
| Text out | `"".join(b.text for b in resp.content if type=="text")` | `resp.choices[0].message.content` (already a string) |
| Token usage | `resp.usage.input_tokens` / `output_tokens` | `resp.usage.prompt_tokens` / `completion_tokens` |
| Resolved model id | `resp.model` | `resp.model` (same) |

**Judge tool-use port (riskiest piece):**
- Tool schema: Anthropic `_JUDGE_TOOL` (`{name, description, input_schema}`)
  → OpenAI `{"type":"function","function":{"name","description","parameters"}}`.
- `tool_choice`: Anthropic `{"type":"any"}` → OpenAI `{"type":"function","function":{"name":...}}` (or `"required"`).
- Extraction: Anthropic reads a `tool_use` block's `.input` (a dict) →
  OpenAI reads `resp.choices[0].message.tool_calls[0].function.arguments`
  (a **JSON string** — must `json.loads`). Update `_extract_tool_input`.
- `_accumulate_usage` reads the renamed token fields (`prompt_tokens`/`completion_tokens`).

## Acceptance criteria

- [ ] All three text SUTs construct an `openai.OpenAI(api_key=…OPENROUTER_API_KEY…, base_url=…)` client and call `chat.completions.create`; no `import anthropic` remains in them.
- [ ] `scorer/judge.py` ported to OpenAI tool-use; `_JUDGE_TOOL`, `_extract_tool_input`, `_accumulate_usage` updated; judge still returns `(score, "judge", rationale)` and still accumulates token usage.
- [ ] SUT self-report unchanged at the harness boundary: each reply still carries `tokens_in`/`tokens_out` (mapped from `prompt_tokens`/`completion_tokens`). **No harness change required** — verify `harness/event_loop.py` accounting still works untouched.
- [ ] Default models updated: SUTs → `deepseek/deepseek-v4-flash`, judge → `moonshotai/kimi-k2.6`.
- [ ] `suts/*/pyproject.toml` and top-level `pyproject.toml` swap the `anthropic` dependency for `openai`; the `no-state-sut` optional-deps group updated.
- [ ] `suts/*/sut-manifest.json` `env` lists updated (`ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY`, add base_url override if declared) and `resource_appendix.model_id` defaults reflect the new models.
- [ ] B4b SUT `Dockerfile`s install `openai` instead of `anthropic` (the shared slim API base + any per-SUT layer). *Full image rebuild stays Docker-blocked under B4c — update the Dockerfile source, note it build-UNVERIFIED.*
- [ ] Tests pass (`pytest -q`). Any test stub/fixture referencing `anthropic` updated (e.g. `harness/stubs`).
- [ ] `run.sh` sources `./.env` if present (`set -a; . ./.env; set +a`) so `OPENROUTER_API_KEY` reaches the harness and is forwarded to SUT subprocesses. No `python-dotenv` dependency.
- [ ] **Live verification:** at least one text SUT driven end-to-end against a real OpenRouter call (using the `.env` key) producing a non-empty trace. Record which SUT + model in the debrief.
- [ ] README packaging/run notes updated where they reference `ANTHROPIC_API_KEY` / Anthropic models.

## Relevant files

- `suts/no_state/no_state/__main__.py` (~80–124: call + client construction)
- `suts/notes_llm/notes_llm/__main__.py` (~144–221)
- `suts/naive_rag/naive_rag/__main__.py` (~388–532; LLM call only — leave embedder seam alone)
- `scorer/judge.py` (~80–169: client, tool schema, extraction, usage)
- `suts/*/sut-manifest.json`, `suts/*/pyproject.toml`, `suts/*/Dockerfile`
- `pyproject.toml` (deps + `no-state-sut` extra)
- `harness/event_loop.py:103` (read-only — confirm boundary accounting unaffected)
- `harness/stubs/__init__.py`, `tests/*`
- `README.md`

## Out of scope

- **The `NAIVE_RAG_EMBEDDER` seam** (sentence-transformers / llama-cpp / fake).
  It's local dense retrieval, not a provider LLM call — OpenRouter doesn't touch
  it. *Deliberate deviation from the original B9 backlog text, which said to fold
  it in.* Routing embeddings through an OpenAI-compatible `/embeddings` endpoint is
  a separate, optional future concern.
- **The boundary token-counting proxy.** Pointing SUTs at a configurable
  `base_url` *unlocks* a local proxy the harness owns that forwards to OpenRouter
  and tallies `usage` at the boundary — shifting token accounting from "trust the
  SUT" to "measured at the boundary." B9 only ensures the `base_url` override seam
  exists; building the proxy is a separate audit-fidelity task (file as a
  follow-up, sits near B10). Today the harness trusts SUT self-report.
- **Validating that an open model judges as well as Claude.** Separate measurement
  study; B9 just makes the judge model configurable + pinned.
- **A general multi-provider framework / plugin registry.** Explicitly not built.
