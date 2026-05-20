# M4 Wire harness + no-state SUT end-to-end

**Priority:** high
**Blocked by:** M2, M3
**Touches:** `harness/`, `suts/no_state/`, `tests/`, possibly minor spec patches under `docs/`

## Context

First integration milestone. M2 built the harness against a stub SUT; M3 built the no-state SUT in isolation. This task wires them together with a trivial task definition (not the smoke test from M5 — even simpler: 1 `READ`, 1 `QUIZ`, 1 `RESET`, 1 `QUIZ`), proves the contract works in practice, and fixes whatever paper-over-the-cracks issues come up.

Expect to find friction: I/O channel mismatches, stage-completion signalling races, `DIR` permission quirks, tagged-section parsing edge cases. This task's value is shaking these out before the smoke test (M7) is in play.

## Goal

Harness + no-state SUT running end-to-end against a minimal task definition, producing a valid trace + snapshot per the M1 schema. Any contract mismatches between M2 and M3 are reconciled here.

## Acceptance criteria

- [ ] A minimal task definition (`tests/fixtures/trivial.yaml` or similar) exists with: 1 `READ` (one paragraph), 1 `QUIZ` (one question, ceiling probe), 1 `RESET`, 1 `QUIZ` (same question, retention@1 probe).
- [ ] `./run.sh tests/fixtures/trivial.yaml` runs to completion with no errors.
- [ ] Output run directory contains:
  - A valid JSONL trace passing schema validation.
  - At least one tarball snapshot under `snapshots/`.
  - Per-`QUIZ` records with `sut_answer` populated from real Anthropic API calls.
- [ ] Integration test in `tests/` that runs the above end-to-end and asserts the trace shape (skipped if `ANTHROPIC_API_KEY` is absent).
- [ ] Any spec patches required to reconcile M2 ↔ M3 contract mismatches are committed alongside; debrief explicitly lists them.

## Relevant files

- `docs/sut-interface.md` (from M3) — the contract under test.
- `docs/trace-schema.md` (from M1) — for trace validation.
- `harness/` (from M2).
- `suts/no_state/` (from M3).

## Decisions already made

- Trivial fixture is intentionally simpler than the M5 smoke test — purpose here is contract integration, not eval semantics.
- Anthropic API key from env; integration test is skipped without it (CI won't have it, but local runs will).

## Out of scope

- Scoring (M6).
- Multi-question QUIZ events (M5 covers that).
- prior probes (also M5 — the trivial fixture only needs ceiling + retention to exercise `RESET`).
- Performance optimisation. Correctness first; this is a smoke run, not a benchmark.

## Notes for the implementer

- If you find yourself wanting to add helper logic into the harness to massage SUT output, **stop**. The harness is thin. If something doesn't work, fix the contract or the SUT, not the harness.
- If you find a spec ambiguity in M1's outputs, patch the doc and note in the debrief.
- Drive-by candidate likely to show up: trace pretty-printer for debugging. Land it as a drive-by if it stays small (<50 lines, no deps).
