# Debrief: M3 SUT interface spec + no-state reference SUT

**Completed:** 2026-05-20
**Commit:** caf7038

## What shipped

- `docs/sut-interface.md` — v1 SUT contract. JSONL framing over
  stdin/stdout (one event in, one response out, EOF = clean exit,
  SIGKILL = RESET), DIR ownership rules (`.harness/` reserved),
  `sut-manifest.json` schema with fields for mode, hardware tier,
  strict-verbatim self-report, entrypoint, env, and resource appendix.
  MUST / MUST-NOT clauses. Worked round-trip example.
- `suts/no_state/` — reference SUT (~101 lines in `__main__.py`).
  Reads JSONL from stdin; on QUIZ parses `<QUESTION id="…">` tags out
  of the tagged STAGE_INPUT, calls the Anthropic Messages API with
  question text only, system-prompts the model to emit
  `<ANSWER id="…">…</ANSWER>` blocks; on READ writes empty
  `stage_output`. Ignores DIR entirely. Defaults to
  `claude-haiku-4-5-20251001`, overridable via `NO_STATE_MODEL`.
  Exits with code 2 (with stderr message) if `ANTHROPIC_API_KEY` is
  missing or `anthropic` is not installed.
- `suts/no_state/sut-manifest.json` declaring `name=no-state`,
  `mode=in-context`, `strict_verbatim=true`, `hardware_tier=API`.
- `suts/no_state/pyproject.toml` pinning `anthropic>=0.39.0`.
- `suts/no_state/README.md` with install + standalone smoke command.

## Descoped / deferred

- Merging the `anthropic` dependency into the root `pyproject.toml`
  — root pyproject is M2's to create, so I declared the dep in the
  SUT's own pyproject for now. Folding it into the root pyproject
  is a post-merge housekeeping task.
- Per-event timeout values — spec'd as "harness implementation-
  defined; M2's call" rather than choosing here.
- Stdout grace period on EOF — same deferral to M2.
- Notes-LLM and naive-RAG reference SUTs (B1, B2) and
  mock-transcript handling (B5) — explicitly out of scope.

## Design decisions

- **Per-event token reporting on the response line.** The pre-locked
  spec said the manifest carries a `resource_appendix`. I added
  optional `tokens_in`, `tokens_out`, `api_call_count`, `notes`
  fields on the per-event response so the harness can aggregate
  resource usage cleanly per event instead of only at end-of-run.
  Documented as optional in the interface spec; absence is fine.
- **System prompt baked in.** The no-state SUT ships a fixed system
  prompt instructing the model to emit `<ANSWER id="…">…</ANSWER>`
  tags. Otherwise raw Haiku output rarely uses the exact tag format
  the trace schema mandates, which would make every quiz parse as
  `not_found` and produce a useless smoke-test floor (would still
  be a valid floor, just an uninformatively degenerate one). The
  prompt does not feed the model any retention-relevant context, so
  it doesn't compromise the no-state property.
- **Batched call per QUIZ.** A QUIZ event may carry multiple
  questions. I batch them into one Anthropic call (single user
  message containing all `<QUESTION>` tags). This both saves
  `api_call_count` and matches what a real in-context SUT would do.
  Alternative (one API call per question) would inflate cost without
  changing the no-state semantics, since the SUT still has no
  access to prior context.
- **Plain regex parser for `<QUESTION>` tags** rather than an XML
  parser — the tagged-section format from decision #2A is
  LLM-native and not strict XML (no root element, entity-escaping
  is uncertain). Regex matches the spirit of the format and is
  robust to the kinds of payloads the harness will actually emit.
- **Manifest `entrypoint` field** added to the manifest schema
  (not pre-locked). The harness needs *some* way to know how to
  launch a given SUT package; baking it into the manifest avoids
  per-SUT special-casing in the harness. Could equally have been
  a separate `run.sh` convention; chose the manifest field for
  introspectability.
- **`env` field in manifest** — names of env vars the SUT requires.
  Declarative rather than implicit; lets the harness fail fast if
  an SUT is missing a required key.

## Observations

- Pre-locked decision said the SUT exits on EOF on stdin. The spec
  also needs to cover the harness's stdin-close grace period and
  the RESET → SIGKILL path; documented both as "harness chooses
  the grace period" so M2 isn't constrained here.
- `docs/protocol.md` describes "clears" as the unit of restart,
  while M1's trace schema uses `RESET`. I kept M3 aligned with M1
  (RESET) and noted in the spec header that protocol.md is
  superseded where they disagree, deferring to backlog B6/B7 for
  a real reconciliation pass.
- Strict request/response ordering within a session is implicit in
  the JSONL design but worth calling out explicitly — agentic SUTs
  with internal async work could otherwise mis-order responses.
- Anthropic SDK `Message.content` is a list of blocks; collapsed
  text-typed blocks to a single string in the SUT. Other block
  types (tool_use, etc.) are dropped, which is fine for a non-
  agentic SUT.

## Follow-ups

### Filed as tasks

None — the obvious post-MVP items (notes-LLM, RAG, root pyproject
merge) are already covered by the existing backlog (B1, B2) or the
M2/M3 merge.

### Considered and dropped

- Adding a `--manifest` flag to the SUT to print the manifest. Not
  needed; the harness reads the file directly.
- Schema validation of incoming events on the SUT side. The contract
  is one-shot per session — if the harness sends a malformed event,
  crashing fast is the right behaviour.
