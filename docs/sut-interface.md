---
title: SUT interface
project: retention-bench
status: v1 — current. Structured answers, entrypoint-array launch, 5-minute per-event timeout.
tags: [spec, data-contract, sut]
---

# SUT interface

The SUT (system under test) is launched and driven by the harness as a subprocess. The interface is intentionally process-level: anything that can be wrapped in a binary that speaks JSON Lines on stdin/stdout is a valid SUT, regardless of language or architecture (pure LLM call, agent scaffold, RAG system, constructive model, …).

It covers the tagged-section `STAGE_INPUT`, strict-verbatim self-report, the process-level contract (and the agentic / in-context leaderboard split), the reference SUT set, resource self-report, and hardware tiers. `docs/trace-schema.md` defines what the harness records about each event.

## Invocation

The harness launches the SUT once per session (a "session" runs from process spawn to `RESET` or end-of-run). The SUT process is:

- Spawned with its **current working directory set to `DIR`** (the per-run persistent directory).
- Inherits the harness's environment, plus any env vars the SUT declares it needs (e.g., `OPENROUTER_API_KEY`).
- Receives no positional command-line arguments by default. SUTs that need configuration knobs read them from `sut-manifest.json` or env vars.
- Connects to the harness via stdin / stdout / stderr (see "I/O channel" below).

The SUT command is read from the manifest's `entrypoint` field as a Docker exec-form argv array (e.g., `["python", "-m", "no_state"]`). SUT developers point the harness at the SUT package directory (`--sut <dir>`); the harness reads `<dir>/sut-manifest.json` and launches what it declares.

### Launch modes

The harness chooses how to launch based on whether the manifest declares an `image`:

- **Subprocess** (no `image`): the harness invokes `subprocess.Popen(entrypoint, cwd=DIR, …)`, inheriting the harness's full environment. This is the path used by the built-in stubs and by tests; it is the original, default launch path.
- **Container** (`image` present): the harness launches the SUT via `docker run -i --rm --name <unique> -v <DIR>:/dir -w /dir <image> <entrypoint…>`. The wire contract is identical — JSONL over the container's stdin/stdout. Differences from the subprocess path:
  - **Environment is not inherited.** Only the env vars named in the manifest's `env` array are forwarded, by name (`docker run -e NAME`), so their values cross into the container without ever appearing in harness logs or process argv. A containerised SUT that needs a var it didn't declare will not see it.
  - **`DIR` is bind-mounted** at the fixed container path `/dir`, which is also the working directory; `RETENTION_BENCH_DIR=/dir` is set so SUTs that read the env var rather than `cwd` resolve it too. The SUT package itself is expected to be installed in the image (no PYTHONPATH injection — that subprocess-only mechanism does not apply).
  - **`RESET` tears the container down by name** (`docker rm -f`) before spawning a fresh one. Killing only the `docker run` client process does not reliably stop the container, so the harness removes it explicitly; this preserves the subprocess path's "RESET = hard kill + fresh spawn" semantics.

**DooD path translation.** When the harness itself runs inside a dev container that mounts the host's `docker.sock` (Docker-outside-of-Docker), the docker *daemon* runs on the host and resolves bind-mount paths against the **host** filesystem. Set `HOST_WORKSPACE` to the host path of the repo root; the harness then rewrites the dev-container `DIR` path (which must live under the repo root) to its host equivalent before passing it to `-v`. On a bare host (harness and daemon share a filesystem) leave `HOST_WORKSPACE` unset and no translation happens. Under the **Sysbox** nested daemon the daemon shares this filesystem, so `HOST_WORKSPACE` is unset and translation is a no-op.

**CL-Bench path (`SubprocessSystem`).** The same `harness.sut_process` engine backs the CL-Bench extension: `retention_bench.SubprocessSystem` launches its SUT in a container when constructed with a `ContainerLaunch(image=…, env_names=…)` (subprocess stays the default). It reuses the identical `docker run` argv, env-by-name forwarding, `DIR`→`/dir` bind-mount, and `docker rm -f`-on-RESET teardown described above. One CL-Bench-specific addition: CL-Bench's runner has no end-of-run hook and never bounces the *last* spawned SUT, so `SubprocessSystem.shutdown()` (or using the system as a context manager) reaps that final container. The two base images and the constructive SUT image are build-verified, and the containerised constructive SUT has been shown to run through CL-Bench's runner under a hard reset with state surviving the container kill.

> **Note:** the harness never hardcodes provider env-var names; it forwards exactly what each manifest's `env` array declares. Switching a SUT's LLM backend is therefore a manifest edit, not a harness change.

## I/O channel

JSON Lines over stdin/stdout. One line = one JSON object = one event. UTF-8. Newline-terminated (LF). No trailing whitespace inside the object; pretty-printing is forbidden because it breaks line framing.

Stderr is reserved for SUT-side diagnostics. The harness captures it but does not parse it.

### Harness → SUT (stdin)

One JSON object per event the SUT must respond to:

```json
{"event_id":"evt-0001","event_type":"QUIZ","stage_input":"<META>...</META>\n<QUESTIONS>...</QUESTIONS>"}
```

Fields:

| Field | Type | Notes |
|---|---|---|
| `event_id` | string | Stable run-local ID. Echoed back in the response. |
| `event_type` | string | `READ` \| `QUIZ`. (`RESET` is signalled by EOF on stdin + process kill; see "Lifecycle".) |
| `stage_input` | string | The tagged-section payload. Already serialised; the SUT does not re-parse JSON to find it. |

The harness will not send a second event line until the SUT has responded to the previous one. The SUT can rely on strict request/response ordering within a session.

### SUT → Harness (stdout)

One JSON object per completed event. Shape depends on `event_type`:

**For `QUIZ` events**, the SUT emits a structured `answers` list:

```json
{"event_id":"evt-0001","answers":[{"id":"q1","text":"travelling salesman"},{"id":"q2","text":"the chief clerk"}]}
```

**For `READ` events**, the SUT emits an acknowledgement (any content):

```json
{"event_id":"evt-0001","stage_output":""}
```

Fields:

| Field | Type | Required for | Notes |
|---|---|---|---|
| `event_id` | string | all | MUST equal the `event_id` of the event being responded to. |
| `answers` | array[object] | QUIZ | One entry per answered question: `{"id": "<question_id>", "text": "<answer>"}`. Order is preserved in the trace; duplicates are recorded as "ambiguous" per-question (harness does not deduplicate). Missing question ids are recorded as "not_found" per-question; the SUT is free to omit answers it doesn't have. |
| `stage_output` | string | READ (conventionally empty) | For READ, a trivial ack — usually `""`. Reserved for future event types that may carry free-form payloads. |

**Why structured answers, not tagged text?** Earlier drafts had the SUT emit `<ANSWER id="…">…</ANSWER>` blocks inside a `stage_output` string and the harness regex-parsed them. This was later changed to make the harness genuinely SUT-agnostic: the harness no longer knows or cares about answer-tag conventions. SUT developers are free to use any internal convention (tagged system-prompt outputs, JSON-mode, structured-output APIs) to extract per-question answers from their underlying model — that's the SUT's business. The wire contract is structured.

Optional fields the SUT MAY include on any response (harness logs them; absence is fine):

| Field | Type | Notes |
|---|---|---|
| `tokens_in` | integer | Tokens consumed for this event (API-tier SUTs). |
| `tokens_out` | integer | Tokens emitted for this event. |
| `api_call_count` | integer | Underlying model invocations made while handling this event. |
| `notes` | string | Free-form SUT-side diagnostic. |

## Lifecycle

```
spawn → [event → response]* → (EOF on stdin → exit) | (SIGKILL on RESET)
```

1. **Spawn.** Harness launches the SUT subprocess in `DIR`. The SUT performs any one-time init (e.g., load model handle, read `DIR` contents from a previous session).
2. **Event loop.** Harness writes event lines to stdin; SUT writes response lines to stdout. Strict one-in-one-out within a session.
3. **End of session.** Two terminations are possible:
   - **Normal end-of-run.** Harness closes the SUT's stdin. SUT MUST detect EOF and exit cleanly (exit code `0`). The harness allows a short grace period (implementation-defined) before escalating to a signal.
   - **`RESET`.** Harness sends `SIGKILL` to the SUT process (no graceful shutdown), snapshots `DIR`, then re-spawns a fresh SUT process pointed at the same `DIR`. The SUT therefore MUST NOT rely on a clean-shutdown hook for persistence — anything that needs to survive a `RESET` must already be on disk before the response that preceded the `RESET` was written.

`RESET` is invisible inside the SUT process: the SUT only ever sees its own session. The new session's process can read `DIR` to discover what its predecessor left behind (or, if it's a no-state SUT, ignore `DIR` entirely).

## `DIR` rules

`DIR` is the per-run persistent directory. It is the SUT's working directory at spawn time.

**The SUT may:**

- Create, read, modify, and delete any file or subdirectory under `DIR`, except those reserved by the harness (see below).
- Assume `DIR` persists across `RESET` within the same run.
- Assume `DIR` is empty on the very first session of a run, unless the task definition declares seed state.

**The SUT MUST NOT:**

- Write outside `DIR` (no `/tmp`, no `$HOME`, no absolute paths). The harness may sandbox this in future; treat it as a contract today.
- Touch anything under the `DIR/.harness/` prefix — this is reserved for harness-side bookkeeping.
- Spawn unkillable child processes. Children MUST exit (or be killable by `SIGKILL` to the parent's process group) within the harness's grace period on `RESET` and end-of-run.
- Assume `DIR` is empty on subsequent sessions — it carries whatever the previous session(s) left.

**Verbatim-caching.** Whether the SUT persists verbatim spans of `READ` text into `DIR` is the SUT's choice; the harness does not enforce. The SUT self-declares `strict_verbatim` in its manifest. Auditors may diff `DIR` snapshots against `READ` payloads post-hoc.

## What the SUT MUST do

1. Read newline-delimited JSON event objects from stdin in order.
2. Write exactly one newline-delimited JSON response per event to stdout, with matching `event_id`.
3. Flush stdout after each response (responses MUST NOT be buffered past the end of the event). Otherwise the harness will block waiting for output that's stuck in a libc buffer.
4. Exit cleanly on stdin EOF.
5. Ship a `sut-manifest.json` (schema below) alongside the SUT entrypoint.

## What the SUT MUST NOT do

1. Reorder or skip events.
2. Emit unsolicited stdout lines (anything not a response to a pending event). Diagnostics belong on stderr.
3. Pretty-print JSON responses (would break line framing).
4. Write outside `DIR` or under `DIR/.harness/`.
5. Block indefinitely. The harness applies a **per-event timeout (default: 300 seconds = 5 minutes)**, overridable per-task via the `event_timeout_seconds` field in the task definition. On timeout the harness SIGKILLs the SUT process and aborts the run with `exit_status: "timeout"` recorded in `run-manifest.json`.

## `sut-manifest.json`

Ships with the SUT package. The harness reads it at run start and copies it into the run directory as `sut-manifest.json` (see `docs/trace-schema.md`).

Schema:

```json
{
  "name": "no-state",
  "version": "0.1.0",
  "mode": "in-context",
  "hardware_tier": "API",
  "strict_verbatim": true,
  "entrypoint": ["python", "-m", "no_state"],
  "env": ["OPENROUTER_API_KEY", "NO_STATE_MODEL", "RETENTION_BENCH_BASE_URL"],
  "resource_appendix": {
    "kind": "api",
    "model_id": "deepseek/deepseek-v4-flash"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Stable SUT name. Used in leaderboard rows. |
| `version` | string | yes | SemVer or freeform; logged for reproducibility. |
| `mode` | enum | yes | `agentic` \| `in-context`. Determines which leaderboard the run lands on. |
| `hardware_tier` | enum | yes | `consumer` \| `1xH100` \| `8xH100` \| `API` \| `open`. |
| `strict_verbatim` | bool | yes | Self-report. `true` means the SUT does not persist verbatim `READ` spans into `DIR`. |
| `entrypoint` | array[string] | yes | argv the harness uses to launch the SUT. In subprocess mode, run in `DIR`; in container mode (see `image`), the in-container argv run with workdir `/dir`. |
| `image` | string | no | Docker image to launch the SUT in. When present, the harness launches via `docker run` instead of a bare subprocess (see "Launch modes"). When absent, the subprocess path is used. |
| `env` | array[string] | no | Env vars the SUT requires (names only — values come from the harness's environment). In container mode these are the **only** vars forwarded into the container (`docker run -e NAME`); in subprocess mode the full environment is inherited and this list is advisory. |
| `resource_appendix` | object | no | Self-reported resource profile. `kind: "api"` → `model_id` etc.; `kind: "local"` → `gpu_model`, etc. Per-event token counts may also be emitted in response lines and aggregated by the harness. |

Missing optional fields are logged but do not fail the run. Missing required fields fail at run start.

## Worked example — one QUIZ round-trip

Harness writes to SUT stdin:

```
{"event_id":"evt-0001","event_type":"QUIZ","stage_input":"<META>\ntype: quiz\nprobe: prior\nevent_id: evt-0001\n</META>\n<QUESTIONS>\n<QUESTION id=\"q1\">What is Gregor's profession?</QUESTION>\n</QUESTIONS>"}
```

SUT writes to its stdout:

```
{"event_id":"evt-0001","answers":[{"id":"q1","text":"travelling salesman"}],"tokens_in":42,"tokens_out":7,"api_call_count":1}
```

The SUT may internally have prompted its underlying model for `<ANSWER>`-tagged output and parsed those tags itself — but that's the SUT's implementation detail; the harness sees only the structured `answers` list.

## Reference implementations

- **`suts/no_state/`** — minimum-viable in-context SUT. Calls an OpenAI-compatible API (via the `openai` SDK pointed at `RETENTION_BENCH_BASE_URL`) with the question text only, ignores `DIR`. Reference for the contract; floor row on the leaderboard.
- **`suts/notes_llm/`** — cumulative-notes SUT; persists running notes to `DIR` and survives `RESET` via them.
- **`suts/naive_rag/`** — naive dense-retrieval RAG SUT; embeds chunks into a `DIR/index.jsonl` index and retrieves at QUIZ time.
- **`suts/constructive/`** — train-and-grow SUT. The only reference that learns by **mutating its own weights** as it reads: each READ takes a bounded next-token gradient step on the READ text and (deterministically, once) grows capacity by adding a transformer block; it flushes a `DIR/checkpoint.pt` (config + weights) *before* each READ ack so the grown model survives `RESET`, and answers QUIZ by generating from current weights. Integration example, not a quality baseline — gibberish answers are expected. Reports `param_count` / `train_steps` / `train_flops` / `growth_count` via the `notes` field.

**A weights-mutating SUT is still a valid `in-context` SUT.** The `agentic | in-context` enum is about *how files reach the model* — the SUT's own scaffold (`agentic`) versus handed to it in context (`in-context`) — not about whether training happens. A SUT that folds `READ` text into its weights and grows its architecture is `in-context` and raises no leaderboard or contract problem: it speaks the same JSONL process contract, persists across `RESET` through `DIR`, and self-declares `strict_verbatim` honestly (weights, not cached verbatim spans). Such a SUT typically declares `hardware_tier: open` and `resource_appendix.kind: "local"`, and produces a **variable-size** `DIR` (storage grows on a growth event) — which the harness already accounts for via the per-`RESET` `DIR` snapshot.

## Cross-references

- `docs/trace-schema.md` — what the harness records about each event, including the `sut-manifest.json` it copies.
- `docs/task-definition-schema.md` — input contract producing the events the SUT sees.
- `docs/metrics.md` — how the SUT's answers become a retention curve.
