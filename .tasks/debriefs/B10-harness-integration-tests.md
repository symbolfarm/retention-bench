# Debrief: B10 Harness integration tests against fake anthropic client

**Completed:** 2026-05-20
**Commit:** 07b741c

## What shipped

- `tests/fake_anthropic_shim/anthropic.py` — minimal shim package that
  shadows the real `anthropic` SDK when its parent dir is on PYTHONPATH.
  Implements only the surface no-state uses: `Anthropic(...)`,
  `client.messages.create(...)`, response with `.content[0].text` and
  `.usage.{input,output}_tokens`. Reads canned responses from a YAML
  fixture pointed to by `FAKE_ANTHROPIC_FIXTURE`; tracks call sequence
  via a counter file at `FAKE_ANTHROPIC_COUNTER` so it persists across
  SUT subprocess respawns.
- `tests/fixtures/fake_anthropic_responses.yaml` — two responses, one
  per QUIZ event, with distinct synthetic token counts so the aggregate
  unambiguously sums both.
- `tests/test_no_state_fake_anthropic.py` — drives the real harness
  against the real `suts/no_state` SUT using the shim. Runs in CI
  without `ANTHROPIC_API_KEY`. Asserts trace shape, sut_invocation_count,
  counter advance (=2), exact aggregate token counts in
  `resource_appendix`, and per-question records.

Both M7 regressions verified caught by reverting each fix in turn:
dropping `extra_pythonpath` from `_run_reset` makes the second SUT
fail to import the shim; dropping the resource-field accumulation
in `_run_quiz` makes the aggregate assertion fail.

## Descoped / deferred

Nothing descoped from the brief.

## Design decisions

All three open questions from the task file were resolved with Toby
up-front (recommended option in each case):

- **Substitution mechanism: PYTHONPATH shim package.** The shim lives
  at `tests/fake_anthropic_shim/anthropic.py` and is prepended to
  PYTHONPATH for the SUT subprocess via `monkeypatch.setenv`. Python's
  import resolution puts PYTHONPATH entries ahead of site-packages, so
  the shim wins over the real `anthropic==0.103.1`. The SUT source is
  untouched.
- **Canned-response shape: sequence-keyed YAML fixture.** The Nth call
  to `messages.create()` returns the Nth response. Counter is persisted
  in a tmp file so the count survives the SUT being killed and respawned
  across RESET — this is what lets the test prove process #2 actually
  used the shim (counter advances from 1 to 2 during the second QUIZ).
- **Resource-field assertions: exact synthetic values.** The fixture
  reports 142+30 input tokens and 23+16 output tokens; the test asserts
  the aggregate matches the sum (172 / 39). Looser "non-zero" would
  pass even if the harness substituted its own counts.

One implicit decision worth flagging: I set `PYTHONPATH` via
`monkeypatch.setenv` on the *test process*, relying on the fact that
`spawn_sut` does `env = os.environ.copy()`. This is in addition to
`config.sut_pythonpath` (which carries the `--sut` package dir). Both
paths converge in `spawn_sut` into the subprocess `PYTHONPATH`. The
shim is on the `os.environ` path; the regression-catching value comes
from the verification step rather than from which slot the path
travels through.

## Observations

- The shim depends on `PyYAML`, which is already a project dependency.
  If we want to make the shim more portable (e.g. usable from a
  pre-installed-deps lightweight CI image), we could inline the
  responses or switch to JSON. Not worth doing now.
- `pyproject.toml` excludes `tests*` from packaging, so the shim won't
  leak into installs. Good as-is.
- The test runs in 0.36s — fast enough that it doesn't justify any
  CI skip annotation. Just runs alongside the unit suite.
- Total suite: 41 passed, 1 skipped (the live-API test, expected
  without `ANTHROPIC_API_KEY`).
- The "trivial" fixture's structure (1 READ, 1 QUIZ, 1 RESET, 1 QUIZ)
  happens to be the minimum that exercises the across-RESET respawn
  path. If we add more reference SUTs (B1, B2), a multi-RESET variant
  of this fixture would catch failure modes that only manifest after
  multiple respawns (e.g. counter drift, file-handle leaks). Filing
  below.

## Follow-ups

### Filed as tasks

None filed. The multi-RESET variant idea is logged below as a
"considered and dropped" rather than filed — it's premature without
real reference SUTs to exercise.

### Considered and dropped

- *Multi-RESET fixture variant.* A version of `trivial.yaml` with 2-3
  RESETs and 3-4 QUIZ events would catch counter drift / file-handle
  leak / monotonic-state regressions across multiple respawns. Dropped
  for now because the marginal coverage is small and B1/B2 (real
  stateful SUTs) will surface those failure modes more directly. Revisit
  if we see a respawn-related bug that only manifests after >1 reset.
- *Generalising the shim into a `fake_*` package family* (e.g. for the
  OpenRouter / pydantic-ai client B9 anticipates). Dropped because
  there's no second consumer yet, and YAGNI. When B9 lands, refactor
  if it makes sense; until then the shim is 80 lines and trivial to
  duplicate if needed.
- *Asserting the SUT's exact prompt content* sent to the fake. Could
  be done by recording calls in the shim. Dropped: that's testing the
  SUT's prompting strategy, which is orthogonal to the harness
  audit-trail fidelity B10 is about.
