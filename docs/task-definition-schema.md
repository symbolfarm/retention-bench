---
title: Task-definition schema
project: retention-bench
status: v1 (MVP) — locked 2026-05-20 (task M1)
tags: [schema, data-contract, tasks]
---

# Task-definition schema

A task definition is the input contract to the harness: it tells the harness which `READ` / `QUIZ` / `RESET` events to run, with which reading materials, against which questions and probes. One task definition + one SUT → one run → one trace (per `trace-schema.md`).

## Format

YAML. Chosen over JSON for editability of multi-line reading material and inline comments. The harness loads via standard YAML 1.2.

## File layout convention

```
tasks/<task_id>/
├── task.yaml            # the task definition (this schema)
├── README.md            # human-readable description, provenance, caveats
├── source.md            # reading material (referenced from task.yaml)
└── questions.yaml       # optional: questions extracted to a separate file
```

Splitting questions and materials out of `task.yaml` is optional but recommended once they grow. The harness resolves `path:` references relative to the task directory.

## Top-level structure

```yaml
task_id: smoke-test
description: |
  Multi-line free text. What this task is, what it tests.
schema_version: 1
event_timeout_seconds: 300       # optional; default 300 (5 min)

materials:
  - id: <material_id>
    path: <relative-path-to-text-file>     # or use `text:` inline
    text: |                                # alternative to `path:`
      <inline text>

questions:
  - id: <question_id>
    text: <question text>
    gold: <gold answer string>
    type: surface_factual | entity_tracking | multi_hop | thematic | retroactive
    material_ref: <material_id>            # which READ delivers what's needed

events:
  - type: quiz | read | reset
    # type-specific fields below
```

## Top-level optional fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `event_timeout_seconds` | integer | 300 | Per-event timeout in seconds. If the SUT does not respond within this window, the harness SIGKILLs it and aborts the run with `exit_status: "timeout"` in `run-manifest.json`. |

## `materials` entries

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable ID, referenced from `READ` events and questions. |
| `path` | string | one of | Relative path to a text file under the task directory. |
| `text` | string | one of | Inline text. Use for very short materials only. |

Exactly one of `path` or `text` is required.

## `questions` entries

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable run-local ID (e.g., `q1`). Referenced from `QUIZ` events. |
| `text` | string | yes | The question as the SUT will see it. |
| `gold` | string | yes | Gold answer. For exact-match scoring (MVP), keep tight (one word or short phrase). Richer schemas land in B3. |
| `type` | enum | yes | Taxonomy per `tasks.md`. |
| `material_ref` | string \| null | yes for non-prior questions | Material this question depends on. Null only for questions intended as pure prior-knowledge probes with no corresponding `READ`. |

## `events` entries

Events run in document order. The harness does not reorder.

### `quiz` events

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | `quiz` | yes | |
| `questions` | array[string] | yes | Question IDs to include in this `QUIZ`. |
| `probe` | enum | yes | `prior` \| `ceiling` \| `retention`. |
| `k` | integer | conditional | Required iff `probe == retention`. Number of `RESET`s between the relevant `READ(s)` and this `QUIZ`. |

Validation:
- `prior` probes must occur before any `READ` of the question's `material_ref`.
- `ceiling` probes must occur after the relevant `READ` and before the next `RESET`, in the same SUT process.
- `retention` probes must be separated from the relevant `READ` by at least `k` `RESET` events.

The harness validates these at load time and refuses to run an ill-formed task.

### `read` events

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | `read` | yes | |
| `material_id` | string | yes | Must match a `materials[].id`. |

The harness loads the material text, wraps it in `<TEXT>…</TEXT>` (with `<META>` per `trace-schema.md`), and delivers it as `STAGE_INPUT`.

### `reset` events

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | `reset` | yes | |

No payload. The harness kills the SUT process, snapshots `DIR`, and spawns a fresh SUT pointed at the same `DIR`.

## Worked example — smoke-test shape

```yaml
task_id: smoke-test
schema_version: 1
description: |
  Toy book-track task for end-to-end smoke testing. Public-domain text;
  ~5 questions; one RESET. Not a cohort-1 asset.

materials:
  - id: source
    path: source.md

questions:
  - id: q1
    text: "What is Gregor's profession at the start of the story?"
    gold: "travelling salesman"
    type: surface_factual
    material_ref: source
  - id: q2
    text: "What does Gregor's family do for income?"
    gold: "they live off Gregor's salary"
    type: surface_factual
    material_ref: source
  - id: q3
    text: "Who first discovers Gregor's transformation?"
    gold: "the chief clerk"
    type: entity_tracking
    material_ref: source
  - id: q4
    text: "What food does Gregor's sister bring him on the second day?"
    gold: "rotten vegetables and old cheese"
    type: surface_factual
    material_ref: source
  - id: q5
    text: "Why does Gregor's father attack him?"
    gold: "to drive him back to his room"
    type: multi_hop
    material_ref: source

events:
  - type: quiz
    questions: [q1, q2, q3, q4, q5]
    probe: prior
  - type: read
    material_id: source
  - type: quiz
    questions: [q1, q2, q3, q4, q5]
    probe: ceiling
  - type: reset
  - type: quiz
    questions: [q1, q2, q3, q4, q5]
    probe: retention
    k: 1
```

Yields a 5-event trace with 15 per-question records (5 questions × 3 probes).

## Validation rules

The harness validates at load time and refuses to run if:

1. A `material_id` referenced from `READ` or a question is not declared in `materials`.
2. A `question_id` referenced from a `QUIZ` is not declared in `questions`.
3. A `prior` probe occurs after a `READ` of its question's `material_ref`.
4. A `ceiling` probe occurs before the relevant `READ`, or after a `RESET` following the `READ`.
5. A `retention` probe has `k` not matching the actual `RESET` count between the relevant `READ` and itself.
6. A `retention` probe occurs before any `RESET`.
7. A material declares both `path` and `text`, or neither.
8. Question IDs or material IDs are non-unique.

Validation failures are reported with a pointer to the offending entry.

## Cross-references

- Decisions #1, #2, #6, #10 in `decisions-checklist.md`.
- `trace-schema.md` — the output contract this input is processed into.
- `tasks.md` — the book-track structure and question taxonomy.
- `protocol.md` — `STAGE_INPUT` framing (some of this doc supersedes earlier protocol-doc statements; protocol.md rewrite is backlog B7).
