---
title: Trace schema
project: retention-bench
status: v1 — current. The harness records the SUT's structured answers directly; it does not parse ANSWER tags out of free text.
tags: [schema, data-contract, trace]
---

# Trace schema

The trace is the data contract between the harness and everything downstream (scorers, audits, leaderboards). One run produces one **run directory** containing a JSONL event stream, a per-question records file, `DIR` snapshots, and two manifests.

## Run directory layout

```
runs/<run_id>/
├── trace.jsonl                   # one record per event (READ, QUIZ, RESET)
├── questions.jsonl               # one record per (question, probe) instance
├── stages/                       # raw STAGE_INPUT / STAGE_OUTPUT payloads
│   ├── <event_id>.in             # what the harness sent to the SUT for this event
│   └── <event_id>.out            # what the SUT wrote back
├── snapshots/                    # DIR tarball per RESET
│   └── reset-<event_id>.tar.gz
├── run-manifest.json             # harness-side run metadata
└── sut-manifest.json             # SUT-side declarations (copied at run start)
```

- `<run_id>` convention: `<task_id>-<iso8601-timestamp>-<short-hash>`. Sortable, traceable.
- `<event_id>` convention: zero-padded sequential, `evt-0001`, `evt-0002`, … . Stable within a run.

Stage payload files (`stages/*.in`, `stages/*.out`) are kept on disk and pointed to by `trace.jsonl` rather than inlined, so the JSONL stays small and greppable even when `READ` events deliver chapter-length text.

## `trace.jsonl` — event stream

One JSON object per line. Common fields on every event:

| Field | Type | Notes |
|---|---|---|
| `event_id` | string | e.g., `evt-0001`. Stable run-local ID. |
| `event_index` | integer | 0-based ordinal in the run. |
| `event_type` | string | `READ` \| `QUIZ` \| `RESET`. |
| `timestamp_start` | string | ISO 8601 UTC. |
| `timestamp_end` | string | ISO 8601 UTC. |
| `wall_clock_ms` | integer | `timestamp_end - timestamp_start` in ms. |
| `sut_process_id` | string | Stable ID of the SUT process this event ran against. Changes on `RESET`. |

Per-type additional fields:

### `READ` events

| Field | Type | Notes |
|---|---|---|
| `material_id` | string | From the task definition; identifies which reading material was delivered. |
| `stage_input_path` | string | Relative path to `stages/<event_id>.in`. Tagged-section format (see the worked example below). |
| `stage_input_bytes` | integer | Byte size of the rendered STAGE_INPUT. |
| `stage_output_path` | string | Relative path. Expected to be empty or a trivial ack. |

### `QUIZ` events

| Field | Type | Notes |
|---|---|---|
| `probe_type` | string | `prior` \| `ceiling` \| `retention`. |
| `k` | integer \| null | For `retention`: number of `RESET`s between the relevant `READ` and this `QUIZ`. Null for `prior` and `ceiling`. |
| `question_ids` | array[string] | Ordered list of question IDs included in this QUIZ. |
| `material_refs` | array[string] | Distinct material IDs referenced by the questions. Useful for filtering. |
| `stage_input_path` | string | Tagged-section STAGE_INPUT with `<QUESTIONS>` section. |
| `stage_output_path` | string | SUT's raw response. Per-question parsing lives in `questions.jsonl`. |

### `RESET` events

| Field | Type | Notes |
|---|---|---|
| `snapshot_path` | string | Relative path to `snapshots/reset-<event_id>.tar.gz`. |
| `dir_uncompressed_bytes` | integer | Sum of file sizes in `DIR` before snapshot. |
| `dir_file_count` | integer | Count of regular files in `DIR` (excluding the `.harness/` prefix the harness reserves). |
| `dir_tarball_bytes` | integer | `tar.gz` size of the snapshot. |
| `sut_kill_signal` | string | Signal used to terminate the SUT process (e.g., `SIGKILL`). |
| `sut_exit_code` | integer \| null | Exit code if observable; null if process was force-killed before exit. |

## `questions.jsonl` — per-question records

One JSON object per (question, probe) instance — i.e., a `QUIZ` of 5 questions emits 5 records. The scorer reads this file exclusively; it never needs to touch `trace.jsonl` or stage payloads.

| Field | Type | Notes |
|---|---|---|
| `record_id` | string | `<event_id>-<question_id>`. Unique. |
| `event_id` | string | The originating `QUIZ` event. |
| `question_id` | string | From the task definition. |
| `probe_type` | string | `prior` \| `ceiling` \| `retention`. Copied from event. |
| `k` | integer \| null | Copied from event. |
| `question_text` | string | Verbatim from task definition. |
| `gold_answer` | string | Verbatim from task definition. Scorer-format (string for exact-match; richer schemas may follow). |
| `sut_answer` | string | SUT's answer to this specific question, parsed out of `stage_output_path`. |
| `question_type` | string | From taxonomy: `surface_factual` \| `entity_tracking` \| `multi_hop` \| `thematic` \| `retroactive`. |
| `material_ref` | string \| null | Which READ this question depends on. Null for purely-prior questions. |
| `question_seen_before` | integer | Count of prior exposures of this question in this run, before the current record. Includes prior `P`, `C`, and earlier `R(k')` instances. |
| `parsing_status` | string | `ok` \| `not_found` \| `ambiguous`. Surfaces SUT-answer-parsing failures without crashing the run. |

### SUT-answer ingestion

For `QUIZ` events, the SUT emits a structured `answers` list directly in its JSONL response (see `sut-interface.md`):

```json
{"event_id":"evt-0003","answers":[{"id":"q1","text":"travelling salesman"}, {"id":"q2","text":"the chief clerk"}]}
```

The harness reads this list and writes one `questions.jsonl` record per question in the originating QUIZ. Per-question record fields are filled in by a simple lookup, not by parsing:

- If the question_id appears exactly once in `answers` → `sut_answer = answers[i].text`, `parsing_status = "ok"`.
- If the question_id is missing from `answers` → `sut_answer = ""`, `parsing_status = "not_found"`. The SUT chose not to (or could not) answer.
- If the question_id appears more than once → `sut_answer = answers[first occurrence].text`, `parsing_status = "ambiguous"`. SUT bug; logged so the scorer can decide whether to score or skip.

The scorer treats `not_found` and `ambiguous` as score = 0 but they remain distinguishable in the records for diagnostics.

The harness is intentionally agnostic to how the SUT produced its answers internally — tagged model outputs, JSON-mode, structured-output APIs, hand-written templates, anything. Earlier drafts had the harness regex-parse `<ANSWER id="…">` tags out of a `stage_output` text blob; this was changed to keep the harness genuinely SUT-agnostic.

## `run-manifest.json` — harness-side run metadata

Single JSON object. Written at run end.

```json
{
  "run_id": "smoke-test-2026-05-20T01-23-45Z-a1b2c3",
  "task_id": "smoke-test",
  "task_path": "tasks/smoke-test/task.yaml",
  "harness_version": "0.1.0",
  "harness_commit": "8b75c9d",
  "started_at": "2026-05-20T01:23:45Z",
  "ended_at":   "2026-05-20T01:25:10Z",
  "wall_clock_ms": 85000,
  "event_count": 7,
  "reset_count": 1,
  "sut_invocation_count": 2,
  "dir_final_uncompressed_bytes": 0,
  "dir_final_file_count": 0,
  "exit_status": "ok"
}
```

- `sut_invocation_count` is the harness-external "tool call"-equivalent for SUT process spawns (no peek into SUT internals).
- `exit_status`: `ok` \| `sut_crash` \| `harness_error` \| `timeout`. `timeout` is set when any event exceeds the configured `event_timeout_seconds` (default 300s); the SUT is SIGKILLed and the run aborts.

## `sut-manifest.json` — SUT declarations

Written by the harness at run start (copied from the SUT package's own `sut-manifest.json`) and re-written at run end with aggregated resource-accounting fields overlaid onto `resource_appendix`. SUT-declared fields (`name`, `version`, `mode`, `hardware_tier`, `strict_verbatim`, plus any non-counter fields under `resource_appendix` such as `gpu_model`) are preserved verbatim; harness-measured counters are written over the top.

Aggregated by the harness at run end:

- `resource_appendix.tokens_in` — sum of `tokens_in` reported by the SUT on each `QUIZ` reply.
- `resource_appendix.tokens_out` — sum of `tokens_out`.
- `resource_appendix.api_call_count` — sum of `api_call_count`.
- `resource_appendix.wall_clock_ms` — total run wall-clock (same value as `run-manifest.json::wall_clock_ms`).
- `resource_appendix.model_id` — overwritten with the last `model_id` the SUT reported in a `QUIZ` reply, if any. Lets the actual model used override a stale static-manifest declaration.

SUTs that don't report these fields keep the static-declared values (or zeros) — missing self-report doesn't fail the run.

The trace contract holds these fields:

```json
{
  "name": "no-state",
  "version": "0.1.0",
  "mode": "in-context",
  "hardware_tier": "API",
  "strict_verbatim": true,
  "resource_appendix": {
    "kind": "api",
    "model_id": "deepseek/deepseek-v4-flash",
    "tokens_in": 12450,
    "tokens_out": 3280,
    "api_call_count": 6
  }
}
```

`mode` ∈ {`agentic`, `in-context`}. `hardware_tier` ∈ {`consumer`, `1xH100`, `8xH100`, `API`, `open`}.

`resource_appendix.kind`:

- `local` → fields: `gpu_model`, `gpu_count`, `train_flops`, `inference_flops`, `wall_clock_ms`.
- `api` → fields: `model_id`, `tokens_in`, `tokens_out`, `api_call_count`.

SUTs write these as best-effort self-reports. Missing fields are logged but don't fail the run.

## Worked example — 3-event trace

Task: one question, one read, one ceiling probe (no RESET, no retention — minimal example for schema clarity).

`trace.jsonl`:

```
{"event_id":"evt-0001","event_index":0,"event_type":"QUIZ","timestamp_start":"2026-05-20T01:23:45.100Z","timestamp_end":"2026-05-20T01:23:46.200Z","wall_clock_ms":1100,"sut_process_id":"sut-01","probe_type":"prior","k":null,"question_ids":["q1"],"material_refs":["source"],"stage_input_path":"stages/evt-0001.in","stage_output_path":"stages/evt-0001.out"}
{"event_id":"evt-0002","event_index":1,"event_type":"READ","timestamp_start":"2026-05-20T01:23:46.300Z","timestamp_end":"2026-05-20T01:23:46.310Z","wall_clock_ms":10,"sut_process_id":"sut-01","material_id":"source","stage_input_path":"stages/evt-0002.in","stage_input_bytes":4321,"stage_output_path":"stages/evt-0002.out"}
{"event_id":"evt-0003","event_index":2,"event_type":"QUIZ","timestamp_start":"2026-05-20T01:23:46.400Z","timestamp_end":"2026-05-20T01:23:47.900Z","wall_clock_ms":1500,"sut_process_id":"sut-01","probe_type":"ceiling","k":null,"question_ids":["q1"],"material_refs":["source"],"stage_input_path":"stages/evt-0003.in","stage_output_path":"stages/evt-0003.out"}
```

`questions.jsonl`:

```
{"record_id":"evt-0001-q1","event_id":"evt-0001","question_id":"q1","probe_type":"prior","k":null,"question_text":"What is Gregor's profession?","gold_answer":"travelling salesman","sut_answer":"Unknown","question_type":"surface_factual","material_ref":"source","question_seen_before":0,"parsing_status":"ok"}
{"record_id":"evt-0003-q1","event_id":"evt-0003","question_id":"q1","probe_type":"ceiling","k":null,"question_text":"What is Gregor's profession?","gold_answer":"travelling salesman","sut_answer":"travelling salesman","question_type":"surface_factual","material_ref":"source","question_seen_before":1,"parsing_status":"ok"}
```

`stages/evt-0001.in` (tagged-section STAGE_INPUT):

```
<META>
type: quiz
probe: prior
event_id: evt-0001
</META>
<QUESTIONS>
<QUESTION id="q1">What is Gregor's profession?</QUESTION>
</QUESTIONS>
```

`stages/evt-0003.out` (raw JSONL SUT response, written verbatim by the harness for audit):

```json
{"event_id":"evt-0003","answers":[{"id":"q1","text":"travelling salesman"}]}
```

## Cross-references

- `task-definition-schema.md` — the input contract this trace is produced against.
- `metrics.md` — the `(R−P)/(C−P)` formula the scorer computes over `questions.jsonl`.
- `sut-interface.md` — the SUT process contract that produces the `stage_output` payloads recorded here.
