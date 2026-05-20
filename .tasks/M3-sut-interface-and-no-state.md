# M3 SUT interface spec + no-state reference SUT

**Priority:** high
**Blocked by:** M1
**Touches:** `docs/sut-interface.md` (new), `suts/no_state/`, `pyproject.toml`

## Context

The SUT contract is what makes retention-bench cross-architecture. Anything that conforms — agent scaffolds, single-shot LLMs, RAG systems, constructive models — is a valid SUT. The contract must be tight enough to be implementable in any language, simple enough that a non-agentic LLM call wrapped in 40 lines of Python is a valid SUT, and disciplined about what the harness will and won't do.

The no-state baseline is the reference implementation: it calls an LLM API with `STAGE_INPUT`, returns the response, ignores `DIR`. It's the first row on the leaderboard and the smoke-test workhorse for M4 + M7.

## Goal

A short spec (`docs/sut-interface.md`) defining the SUT binary contract, plus a working no-state reference SUT that conforms to it and talks to the Anthropic API.

## Acceptance criteria

- [ ] `docs/sut-interface.md` exists and specifies:
  - SUT invocation: how the harness launches the SUT (command-line args, env vars, working directory = `DIR`).
  - I/O channel: where the SUT reads `STAGE_INPUT`, where it writes `STAGE_OUTPUT`, signalling completion of a stage.
  - Lifecycle: SUT runs across multiple stages within one process; `RESET` = process kill, no graceful shutdown.
  - `DIR` rules: SUT owns its contents; harness reserves `.harness/` prefix; everything else is fair game.
  - What the SUT MUST do: read `STAGE_INPUT`, write `STAGE_OUTPUT` per stage, exit on EOF.
  - What the SUT MUST NOT do: write outside `DIR`; spawn unkillable children; assume `DIR` is empty on startup (it persists across `RESET`).
  - Self-reported metadata: optional `sut-manifest.json` declaring `(name, version, mode ∈ {agentic, in-context}, hardware_tier, strict_verbatim: bool)` consumed by the harness for the trace appendix.
- [ ] `suts/no_state/` contains a working Python reference SUT:
  - Reads `STAGE_INPUT`, parses the tagged sections.
  - On `STAGE_META.type == read`: writes an empty `STAGE_OUTPUT` (no-state has nothing to do).
  - On `STAGE_META.type == quiz`: calls the Anthropic API with the question text *only* (no prior context — that's the whole point of no-state), writes the response to `STAGE_OUTPUT`.
  - Ignores `DIR` entirely.
  - Includes a `sut-manifest.json` declaring `(name=no-state, mode=in-context, strict_verbatim=true)`.
- [ ] `anthropic` dependency added to `pyproject.toml`.
- [ ] Smoke test: the no-state SUT can be invoked standalone (outside the harness) with a fake `STAGE_INPUT` file and produce a non-empty `STAGE_OUTPUT`.
- [ ] Anthropic API key sourced from `ANTHROPIC_API_KEY` env var; SUT errors clearly if absent.
- [ ] Model defaults to `claude-haiku-4-5-20251001` (cheapest current Claude) for smoke testing; overridable via `sut-manifest.json` or env var.

## Relevant files

- `docs/decisions-checklist.md` (#2, #4, #7, #11) — tagged-sections, strict-verbatim self-report, two-leaderboard, reference SUT set.
- `docs/protocol.md` — current protocol framing.
- `docs/trace-schema.md` (M1) — for understanding what metadata the harness expects from the SUT.

## Decisions already made

- No-state is one of the three reference SUTs (#11B).
- Strict verbatim is self-reported (#4 Toby's amendment). No-state has nothing to copy, so it trivially declares `strict_verbatim=true`.
- SUT contract is process-level (#7 resolution: agentic SUTs handle their own tools; non-agentic SUTs receive mock transcripts in `STAGE_INPUT`). No-state is the prototypical non-agentic SUT.
- Default Claude model is Haiku 4.5 for cost; Opus 4.7 is the most capable model but smoke testing should be cheap.

## Out of scope

- notes-LLM, naive-RAG reference SUTs (B1, B2).
- Mock tool-call transcript generation (B5).
- Multi-model / model-router SUTs.
- Local-model SUTs (out of scope for MVP; the API tier covers smoke testing).

## Notes for the implementer

- Coordinate the I/O channel decision with M2 — both must agree on file paths and signalling. Default proposal: `DIR/.harness/in` is the harness-written `STAGE_INPUT`; SUT signals stage completion by writing `DIR/.harness/out` and the harness picks it up. If M2 chose pipes instead, follow that.
- Keep the no-state SUT under 100 lines if at all possible — it's a reference, not an architecture.
