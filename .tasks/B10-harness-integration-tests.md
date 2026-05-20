# B10 Harness integration tests against a fake-anthropic client

**Priority:** medium
**Blocked by:** nothing
**Touches:** `tests/`, `tests/fixtures/`, possibly `suts/no_state/`, possibly `harness/sut_process.py`

## Context

M7's end-to-end smoke run surfaced two harness bugs that no test caught:

1. `_run_reset` dropped `PYTHONPATH` when respawning the SUT subprocess.
2. SUT-reported resource fields (token counts, etc.) were silently dropped
   on the floor rather than written into the trace.

The existing unit suite exercises the harness against a stub SUT
(`harness/stubs/echo_sut.py`), which doesn't go through the real
subprocess + Anthropic SDK + token-accounting path. The only test that
*does* (`tests/test_no_state_integration.py`) is gated on
`ANTHROPIC_API_KEY` and hits the live API — so it doesn't run in CI and
burns tokens locally.

Retention-bench has a dual purpose ([[project_cleval_dual_purpose]]):
internal infra + public-credibility artifact. Once we start publishing
real curves from B1/B2 SUTs, audit-trail fidelity matters — silent
mis-aggregation in the harness would damage credibility. B10 protects
that surface before we get there.

## Goal

A CI-runnable integration test that drives the **real no-state SUT**
through the **real harness** with a **fake `anthropic.Anthropic`**
client substituted at the SDK boundary. Returns canned responses +
synthetic token counts. Regression-protects the two M7 bugs and the
broader class of "harness loses information between the SUT subprocess
and the trace."

## Acceptance criteria

- [ ] New test file (e.g. `tests/test_no_state_fake_anthropic.py`)
      that runs without `ANTHROPIC_API_KEY` set.
- [ ] Test drives the real harness against the real `suts/no_state` SUT,
      with `anthropic.Anthropic` replaced by a fake.
- [ ] Fake returns deterministic canned responses keyed somehow
      (per-call sequence, prompt-hash, or fixture-driven — design call).
- [ ] Fake reports synthetic token counts so the resource-field path
      is exercised.
- [ ] Assertions cover: trace event sequence, per-question records,
      `PYTHONPATH` survives `RESET` (regression for bug #1), resource
      fields land in the trace (regression for bug #2).
- [ ] Existing tests still pass.
- [ ] Test passes locally without an API key.

## Relevant files

- `tests/test_no_state_integration.py` — current live-API integration
  test, the model for the fake-driven one.
- `harness/sut_process.py` — subprocess lifecycle (where `_run_reset`
  lives or used to).
- `harness/event_loop.py` — drives READ/QUIZ/RESET; where resource
  fields flow from SUT response into trace.
- `harness/trace_writer.py` — final landing zone for resource fields.
- `suts/no_state/no_state` — SUT entrypoint; how it imports anthropic.
- `suts/no_state/sut-manifest.json` — entrypoint declaration.
- `harness/stubs/echo_sut.py` — existing stub pattern.

## Decisions already made

- The fake must drive the **real** subprocess + harness path, not a
  monkey-patched in-process call. The whole point is to catch
  cross-process information loss.
- No live API key in CI. The fake replaces the SDK boundary.

## Open design questions (resolve with user before coding)

- **Substitution mechanism.** Three candidates:
  (a) `conftest.py` injects an env var that the SUT reads and uses to
      construct a fake client instead of the real one.
  (b) A `fake_anthropic` shim package on `PYTHONPATH` that shadows
      the real `anthropic` import.
  (c) The SUT grows a `--fake` flag.
- **Canned-response shape.** Hardcoded in the fake? YAML fixture keyed
  by prompt-hash? Sequence-based (Nth call returns Nth response)?
- **Resource-field assertions.** Exact token counts vs. just "present
  and non-zero"?

## Out of scope

- Notes-LLM SUT (B1) — separate task.
- LLM-judge scorer (B3) — separate.
- Refactoring the live-API integration test — leave it as-is, gated
  on the key.
- Generic LLM-backend abstraction (B9) — orthogonal.
