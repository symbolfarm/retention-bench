---
title: SUT interface
project: retention-bench
status: v2 — current. `SubprocessSystem` one-line-JSON query/reply per CL-Bench instance; subprocess / container launch; hard-reset survive-dir.
tags: [spec, data-contract, sut]
---

# SUT interface

The SUT (system under test) is launched and driven by retention-bench as a subprocess that speaks **one JSON object per line** on stdin/stdout. The interface is intentionally process-level: anything that can be wrapped in a binary speaking JSON Lines is a valid SUT, regardless of language or architecture (pure LLM call, agent scaffold, RAG system, constructive train-and-grow model, …).

The live contract is [`retention_bench.SubprocessSystem`](../retention_bench/system.py): it wraps the SUT process as a Continual Learning Bench `ContinualLearningSystem`, drives it through CL-Bench's runner, and adds the two things CL-Bench cannot natively express — a **hard `RESET`** (SIGKILL + respawn, where only an on-disk survive-dir persists) and a **system-side reset schedule** (arbitrary reset density `k`). This doc covers the query/reply wire shape, the survive-dir / `RESET` mechanics, resource self-report, launch (subprocess / container), and the `sut-manifest.json` declaration.

## Invocation

`SubprocessSystem` launches the SUT once per *session* — a session runs from process spawn to the next hard `RESET` (or end-of-run). The SUT process is:

- Spawned with its **current working directory set to the survive-dir** (the per-run persistent directory; equivalently `RETENTION_BENCH_DIR`, which the harness exports).
- Inherits the harness's environment (subprocess mode) plus any env vars the SUT declares it needs (e.g., `OPENROUTER_API_KEY`).
- Receives no positional command-line arguments by default. SUTs that need configuration knobs read them from env vars.
- Connects to the harness via stdin / stdout / stderr (see "I/O channel" below).

The SUT launch command is the `command` passed to `SubprocessSystem` — for example `["python", "-m", "bsm_accumulator.clbench_main"]`. On the `gain_curve` CLI it is the `--sut` string (`--sut "python -m bsm_accumulator.clbench_main"`, `shlex`-split). A `python`/`python3` argv[0] is rewritten to the harness interpreter, and `--extra-pythonpath` dirs are prepended to the SUT's `PYTHONPATH` so an uninstalled SUT package resolves.

> **The live harness does not read `sut-manifest.json`.** The manifest (below) is a packaging/declaration artifact that ships with a SUT and records its canonical launch argv (`clbench_entrypoint`), hardware tier, and resource profile for humans and tooling. The live `SubprocessSystem` path takes the command directly (from `--sut` / the `command` arg); it does not parse the manifest. Keep the manifest's `clbench_entrypoint` in sync with the command you actually launch.

### Launch modes

`SubprocessSystem` launches as a bare host subprocess by default. Pass a `ContainerLaunch(image=…, env_names=…)` to launch inside a container instead (the subprocess path is the default and the only one the `gain_curve` CLI currently exposes; container launch is programmatic). Both reuse the same `harness.sut_process` engine.

- **Subprocess** (default): `subprocess.Popen(command, cwd=<survive-dir>, …)`, inheriting the harness's full environment. This is the path the smoke run, the `gain_curve` CLI, and the tests use.
- **Container** (`ContainerLaunch`): the SUT is launched via `docker run -i --rm --name <unique> -v <survive-dir>:/dir -w /dir <image> <command…>`. The wire contract is identical — JSONL over the container's stdin/stdout. Differences from the subprocess path:
  - **Environment is not inherited.** Only the env vars named in `env_names` are forwarded, by name (`docker run -e NAME`), so their values cross into the container without ever appearing in harness logs or process argv. A containerised SUT that needs a var it didn't declare will not see it.
  - **The survive-dir is bind-mounted** at the fixed container path `/dir`, which is also the working directory; `RETENTION_BENCH_DIR=/dir` is set so SUTs that read the env var rather than `cwd` resolve it too. The SUT package itself is expected to be installed in the image (no `PYTHONPATH` injection — that subprocess-only mechanism does not apply, so `command` must name an entrypoint the *image* provides, e.g. `["python", "-m", "constructive.clbench_main"]`).
  - **`RESET` tears the container down by name** (`docker rm -f`) before spawning a fresh one. Killing only the `docker run` client process does not reliably stop the container, so the harness removes it explicitly; this preserves the "RESET = hard kill + fresh spawn" semantics.
  - **End-of-run teardown.** CL-Bench's runner has no end-of-run hook and never bounces the *last* spawned SUT, so call `SubprocessSystem.shutdown()` (or use the system as a context manager) to reap that final container. The two base images and the constructive SUT image are build-verified, and the containerised constructive SUT has run through CL-Bench's runner under a hard reset with state surviving the container kill.

**DooD path translation.** When the harness itself runs inside a dev container that mounts the host's `docker.sock` (Docker-outside-of-Docker), the docker *daemon* runs on the host and resolves bind-mount paths against the **host** filesystem. Set `HOST_WORKSPACE` to the host path of the repo root (the survive-dir must live under it); the harness rewrites the dev-container survive-dir path to its host equivalent before passing it to `-v`. On a bare host — or under the Sysbox nested daemon — the daemon shares this filesystem, so leave `HOST_WORKSPACE` unset and translation is a no-op.

> **Note:** the harness never hardcodes provider env-var names; it forwards exactly the `env_names` a `ContainerLaunch` declares. Switching a SUT's LLM backend is a launch-config / env edit, not a harness change.

## I/O channel

JSON Lines over stdin/stdout. One line = one JSON object = one event. UTF-8. Newline-terminated (LF). No trailing whitespace inside the object; pretty-printing is forbidden because it breaks line framing.

Stderr is reserved for SUT-side diagnostics. The harness captures it but does not parse it.

### Harness → SUT (stdin): one query per line

One JSON object per CL-Bench instance the SUT must respond to:

```json
{"prompt":"<rendered instance text>","instance_id":"inst-0007","instance_index":7,"response_schema":{"type":"object","properties":{"transmitters":{"type":"array","items":{"$ref":"#/$defs/Transmitter"}}},"required":["transmitters"],"$defs":{"...":"..."}},"feedback":null}
```

Fields:

| Field | Type | Notes |
|---|---|---|
| `prompt` | string | The rendered CL-Bench instance text — the observation and the request for a structured report, already serialised. The SUT does not re-parse JSON to find it. |
| `instance_id` | string \| null | Stable run-local instance ID. Echoed into the harness trace; not required in the reply. |
| `instance_index` | integer \| null | 0-based ordinal of the instance within the run. |
| `response_schema` | object | The **JSON Schema** of the task's expected response model. The reply's `action` MUST conform to it. |
| `feedback` | string \| null | Optional feedback string the task supplied for this instance (CL-Bench feedback channel); `null` when none. |

The harness will not send a second query line until the SUT has responded to the previous one. The SUT can rely on strict request/response ordering within a session.

### SUT → Harness (stdout): one reply per line

One JSON object per completed query:

```json
{"action":{"transmitters":[{"center_freq":32.3,"bandwidth":14.8,"currently_active":true,"estimated_power":-39.0}]},"resource":{"flops":100,"tokens_in":256,"tokens_out":1,"model_id":"bsm-accumulator"}}
```

Fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | object | yes\* | Fields matching `response_schema`. The harness constructs `response_schema(**action)`, so the keys and types must satisfy the schema. |
| `resource` | object | no | Free-form resource self-report (see below). The key is reserved. |

**\*The `action` wrapper is optional for trivial SUTs.** If the reply has no `action` key, the harness treats the **whole reply object minus the reserved `resource` key** as the action fields. So `{"transmitters":[…],"resource":{…}}` and `{"action":{"transmitters":[…]},"resource":{…}}` are equivalent.

**`resource` self-report.** Free-form; the harness lifts the recognised keys onto a per-response compute `UsageEvent` and preserves the whole dict under `metadata["sut_resource"]`. Recognised keys:

| Key | Type | Notes |
|---|---|---|
| `flops` | integer | Compute spent handling this query (parametric / constructive SUTs). |
| `tokens_in` | integer | Tokens consumed for this query (API-tier SUTs). |
| `tokens_out` | integer | Tokens emitted for this query. |
| `model_id` | string | Underlying model identifier; defaults to the system name if absent. |

Any other keys (e.g. `api_call_count`, `param_count`, `train_steps`, `growth_count`) are preserved under `sut_resource` and surface in the trace, but are not specially interpreted. A no-state or counter SUT may omit `resource` entirely; the harness still records a zero-cost compute marker so there is one compute event per response regardless of SUT class.

**Why a `response_schema`, not a fixed answer shape?** The book-track predecessor sent tagged `QUIZ` events and parsed a fixed `answers:[{id,text}]` list. The CL-Bench-native contract is generic: each task declares its own response model, the harness ships its JSON Schema per query, and the SUT returns any object conforming to it. The harness stays genuinely task-agnostic — how the SUT derives a conforming object from its model (tool-calling, JSON mode, structured-output APIs, regex over the prompt) is the SUT's business.

## Lifecycle

```
spawn → [query → reply]* → (EOF on stdin → exit) | (SIGKILL on RESET)
```

1. **Spawn.** Harness launches the SUT process in the survive-dir. The SUT performs any one-time init (load a model handle, read survive-dir contents left by a previous session).
2. **Query loop.** Harness writes one query line to stdin; SUT writes one reply line to stdout. Strict one-in-one-out within a session.
3. **End of session.** Two terminations are possible:
   - **`RESET`.** Between CL-Bench instances, when the system-side reset schedule fires, the harness sends `SIGKILL` to the SUT's **process group** (no graceful shutdown), then re-spawns a fresh SUT pointed at the same survive-dir. In subprocess mode the SUT is launched in its own session (`start_new_session=True`), so the kill signals the whole group and any children the SUT spawned die with it — the discontinuity is mechanical, not trust-based. The SUT therefore MUST NOT rely on a clean-shutdown hook for persistence — anything that must survive a `RESET` has to already be on disk before the reply that preceded the `RESET` was written.
   - **End-of-run.** The harness closes the SUT's stdin; the SUT MUST detect EOF and exit cleanly (exit code `0`). Because CL-Bench's runner never bounces the *last* SUT, end-of-run reaping is driven by `SubprocessSystem.shutdown()` / context-manager exit.

`RESET` is invisible inside the SUT process: each session only ever sees its own queries. A fresh session can read the survive-dir to discover what its predecessor left behind (or, if it's a no-state SUT, ignore the survive-dir entirely). The stateless-baseline arm of a gain-curve sweep additionally **wipes** the survive-dir on each reset (`wipe_on_reset=True`) — see [`metrics.md`](metrics.md).

## Survive-dir rules

The survive-dir is the per-run persistent directory and the SUT's working directory at spawn. It is the **only** thing that crosses a hard `RESET`.

**The SUT may:**

- Create, read, modify, and delete any file or subdirectory under the survive-dir, except those reserved by the harness (below).
- Assume the survive-dir persists across `RESET` within the same run (unless the arm wipes it).
- Assume the survive-dir is empty on the very first session of a run.

**The SUT MUST NOT:**

- Write outside the survive-dir (no `/tmp`, no `$HOME`, no absolute paths). Treat it as a contract today; the harness may sandbox it in future.
- Touch anything under the `.harness/` prefix inside the survive-dir — reserved for harness-side bookkeeping.
- Spawn unkillable child processes. On `RESET` and end-of-run the harness `SIGKILL`s the SUT's entire process group, so ordinary children die with the parent; this is enforced (subprocess mode: `start_new_session` + `killpg`; container mode: `docker rm -f` tears down the whole container). A SUT MUST NOT detach a child into a *new* session/process group or a daemon that outlives the group kill (e.g. a `setsid` helper, or a server registered with the host init) — such a survivor could carry in-memory state across the discontinuity and is a benchmark-integrity violation.
- Assume the survive-dir is empty on subsequent sessions — it carries whatever previous session(s) left.

**Flush-before-reply.** Because `RESET` is a SIGKILL with no warning, any state the SUT wants to retain must be on disk *before* the reply that precedes the reset. The reference SUTs flush their state file (atomically — write-temp-then-`os.replace`) before writing each reply line.

**Verbatim-caching.** Whether the SUT persists verbatim spans of the observation text into the survive-dir is the SUT's choice; the harness does not enforce. The SUT self-declares `strict_verbatim` in its manifest. Auditors may diff survive-dir snapshots against the prompts post-hoc.

## What the SUT MUST do

1. Read newline-delimited JSON query objects from stdin in order.
2. Write exactly one newline-delimited JSON reply per query to stdout, whose `action` conforms to that query's `response_schema`.
3. Flush stdout after each reply (replies MUST NOT be buffered past the end of the query). Otherwise the harness blocks waiting for output stuck in a libc buffer.
4. Exit cleanly on stdin EOF.
5. Persist anything that must survive a `RESET` to the survive-dir *before* the preceding reply.

## What the SUT MUST NOT do

1. Reorder or skip queries.
2. Emit unsolicited stdout lines (anything not a reply to a pending query). Diagnostics belong on stderr.
3. Pretty-print JSON replies (would break line framing).
4. Write outside the survive-dir or under its `.harness/` prefix.
5. Block indefinitely. The harness applies a **per-response timeout (default: 300 seconds = 5 minutes)**, set via `SubprocessSystem(timeout_s=…)` / `gain_curve --timeout`. On timeout the harness `SIGKILL`s the SUT's process group (the same whole-tree kill a `RESET` uses — no wedged survivor is left to linger until end-of-run) and raises `SUTTimeout`; a mid-run crash (the SUT closing stdout before replying) is likewise reaped and surfaced as an `SUTError`.

## `sut-manifest.json`

Ships with the SUT package as its declaration of record. The live `SubprocessSystem` path does not read it (the command is supplied directly), but it is the human- and tooling-facing source of truth for how to launch the SUT and what it costs. Canonical example — the keyless accumulator that backs the offline smoke (`suts/bsm_accumulator/sut-manifest.json`):

```json
{
  "name": "bsm-accumulator",
  "version": "0.1.0",
  "mode": "notes",
  "hardware_tier": "open",
  "strict_verbatim": true,
  "image": null,
  "clbench_entrypoint": ["python", "-m", "bsm_accumulator.clbench_main"],
  "env": [],
  "resource_appendix": {
    "kind": "local",
    "model_id": "bsm-accumulator",
    "gpu_model": null
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Stable SUT name. Used as the system / leaderboard-row label. |
| `version` | string | yes | SemVer or freeform; logged for reproducibility. |
| `mode` | string | yes | Descriptive **system-class** self-label — e.g. `in-context`, `notes`, `agentic`, `constructive`. Informational only (see "System class & leaderboard" below); it does not route the SUT to a separate leaderboard. |
| `hardware_tier` | enum | yes | `consumer` \| `1xH100` \| `8xH100` \| `API` \| `open`. |
| `strict_verbatim` | bool | yes | Self-report. `true` means the SUT does not persist verbatim observation spans into the survive-dir. |
| `clbench_entrypoint` | array[string] | yes | The live wire launch argv — the `command` you pass to `SubprocessSystem` / `--sut`. The CL-Bench-native entrypoint (e.g. `…clbench_main`). |
| `image` | string \| null | no | Docker image to launch the SUT in (paired with a `ContainerLaunch`). `null` / absent → subprocess. |
| `env` | array[string] | no | Env vars the SUT requires (names only — values come from the harness's environment). In container mode these are the **only** vars forwarded (`docker run -e NAME`); in subprocess mode the full environment is inherited and this list is advisory. |
| `resource_appendix` | object | no | Self-reported resource profile. `kind: "api"` → `model_id` etc.; `kind: "local"` → `model_id`, `gpu_model`, etc. Per-response token/FLOP counts are also emitted in reply `resource` objects and aggregated by the harness. |

## Worked example — one query round-trip

The keyless `bsm_accumulator` SUT on CL-Bench's `blind_spectrum_monitoring`. Harness writes to SUT stdin (abridged schema):

```
{"prompt":"Spectrum scan 7...\n  - peak_id: peak-12 | freq: 32.3 MHz | power: -39.0 dBm | width: 14.8 MHz\n...","instance_id":"inst-0007","instance_index":7,"response_schema":{"type":"object","properties":{"transmitters":{"type":"array"}},"required":["transmitters"]},"feedback":null}
```

The SUT parses this scan's peaks from `prompt`, unions them into its survive-dir state file (flushed atomically *before* replying, so it survives a `RESET` SIGKILL), and reports every transmitter accumulated so far. It writes to stdout:

```
{"action":{"transmitters":[{"center_freq":32.3,"bandwidth":14.8,"currently_active":true,"estimated_power":-39.0}]},"resource":{"flops":100,"tokens_in":256,"tokens_out":1,"model_id":"bsm-accumulator"}}
```

A reset between instance 7 and the next instance would SIGKILL this process; the fresh process re-reads the survive-dir on spawn and continues from the accumulated set (or, in the stateless-baseline arm, finds the survive-dir wiped and starts cold).

## System class & leaderboard

retention-bench does **not** maintain its own `agentic | in-context` two-leaderboard split. CL-Bench owns the leaderboard; retention-bench contributes the net-new **reset-density `k` axis** (see [`metrics.md`](metrics.md)) over the same systems. The manifest's `mode` is therefore a *descriptive* system-class self-label, not a leaderboard router.

A weights-mutating, train-and-grow SUT is a first-class system here: it speaks the same one-line-JSON process contract, persists across `RESET` through the survive-dir, and self-declares `strict_verbatim` honestly (weights, not cached verbatim spans). Such a SUT typically declares `hardware_tier: open` and `resource_appendix.kind: "local"`, reports `flops` / `param_count` / `train_steps` / `growth_count` in its reply `resource`, and produces a **variable-size** survive-dir (storage grows on a growth event) — which the harness already accounts for via the per-instance storage `UsageEvent`.

## Reference implementations

Three reference SUTs ship (the pre-pivot book-track `no_state` and `naive_rag` SUTs were dropped: the gain-curve's prior arm `P` supplies the stateless floor intrinsically, and CL-Bench ships stateless / Mem0 baselines).

- **`suts/bsm_accumulator/`** — keyless, stdlib-only accumulator. Drives `blind_spectrum_monitoring` with **no API key and no model weights**: it unions every peak it has seen into a survive-dir JSON (flushed atomically before each reply) and reports the accumulated set each scan. Backs the canonical offline `./run.sh smoke`; the cleanest illustration of the hard-reset thesis (state survives the kill via the survive-dir).
- **`suts/notes_llm/`** — cumulative-notes SUT. Per query it makes one LLM call to revise `DIR/notes.md` from the new observation, then a second call to emit a `response_schema`-conforming report from the notes alone; the notes are the retained artifact and survive `RESET`. Calls an OpenAI-compatible API (via the `openai` SDK pointed at `RETENTION_BENCH_BASE_URL`).
- **`suts/constructive/`** — train-and-grow SUT. The only reference that learns by **mutating its own weights**: each query takes a bounded next-token gradient step on the prompt and (deterministically, once) grows capacity by adding a transformer block; it flushes `DIR/checkpoint.pt` (config + weights) before replying, so the grown model survives `RESET`, and answers by generating from current weights. Integration example, not a quality baseline — gibberish answers are expected. Reports `param_count` / `train_steps` / `train_flops` / `growth_count` via the reply `resource`.

## Cross-references

- [`metrics.md`](metrics.md) — how the SUT's per-instance rewards become a reset-axis retention curve.
