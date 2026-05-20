# Debrief: M7 End-to-end smoke run

**Completed:** 2026-05-20
**Commit:** 2065ae3

## What shipped

The MVP milestone. `./run.sh smoke` runs the M5 smoke-test task end-to-end against the no-state reference SUT, scores the resulting trace with M6, and prints the retention curve. No manual steps between harness exit and scorer invocation.

- `run.sh` — gained a `smoke` subcommand that captures the harness's printed run-dir on stdout and pipes it to `python -m scorer`. Also sources `.env` so callers don't have to export keys.
- `tasks/smoke-test/sample-output.md` — captured-output reference. Documents the expected `C≈P` exclusion behaviour for the no-state SUT.
- `README.md` — Quickstart section.
- `docs/trace-schema.md` — clarified that `sut-manifest.json::resource_appendix` is overlaid with run-end aggregated values, not just copied verbatim from the SUT package.
- `.gitignore` — adds `.env` exclusion (with `.env.example` allow-list for future use).
- `TASKS.md` — backlog B9 filed (generic LLM-backend).

Two real harness patches landed in this commit (small, scope-appropriate per M7's "natural place to surface seams" framing):

- `harness/event_loop.py::_run_reset` — passes `extra_pythonpath=config.sut_pythonpath` to the respawn. The initial `spawn_sut` was already passing this; the respawn dropped it, breaking any module-entrypoint SUT after the first `RESET`.
- `harness/event_loop.py` — `_RunState` accumulates `tokens_in/tokens_out/api_call_count` and tracks the last `model_id` reported by the SUT on `QUIZ` replies; at run end, these are merged into `sut-manifest.json::resource_appendix` and the manifest is rewritten.
- `suts/no_state/no_state/__main__.py` — one extra field (`model_id`) in `QUIZ` replies, so the harness can write through the actual model used (rather than the static-declared default).

40 tests + 1 skip still pass after the patches.

## Descoped / deferred

- LLM-judge scoring (B3) — exact-match showed predictable false-negatives on verbose answers in the smoke run; B3 will address.
- DeepSeek / OpenRouter / pydantic-ai backend abstraction (now B9). Surfaced today when Haiku 4.5 was overloaded mid-task.
- Generalised retry/backoff in the no-state SUT. Anthropic SDK has 2x built-in retries which weren't enough during the 529 wave; not patched because switching models was simpler. Could revisit if 529s become routine.
- A `runs/latest` symlink. Decided against patching the harness — the wrapper captures the harness's printed run-dir on stdout, which is equally good and more local. Considered-and-dropped (see Follow-ups).

## Design decisions

- **Wrapper captures run-dir via stdout rather than a `runs/latest` symlink.** The harness prints the run-dir as its last line of stdout; `run.sh` does `tee /dev/stderr | tail -n 1` to capture it while keeping it visible to the user. Avoids a new harness side-effect (symlink creation) for a problem solvable in the wrapper.

- **Harness patches land in M7 rather than as separate follow-ups.** The brief's "small patches land here, large patches get filed" rule. Both patches are <20 LOC each, fix concrete blockers for AC#6 / smoke completion, and don't change any locked contract. The trace-schema doc was updated in the same commit to keep docs and code in sync.

- **`sut-manifest.json` rewrite-at-end strategy.** Instead of streaming per-event resource records or building up a separate manifest, the harness just overwrites the manifest at run end with the static dict + dynamic overlay. Simplest possible — the manifest is small and only read after the run completes.

- **`model_id` reported per-`QUIZ` reply, harness keeps the last value.** SUTs in principle could switch models mid-run; for now they don't, but the last-write-wins design is robust to it and doesn't add complexity. Documented in `docs/trace-schema.md`.

- **Switched to Sonnet 4.6 mid-task because Haiku 4.5 was 529-overloaded.** Toby approved. Cost rose from ~$0.005 to ~$0.015 per smoke run — trivial vs the $10 budget. Documented in `sample-output.md`. The static `sut-manifest.json` still defaults to Haiku; the actual model used flows through `resource_appendix.model_id` via the new SUT-self-report path.

- **`.env` sourcing in the wrapper, no Python-side dotenv loader.** Per M5's "no scope creep" pattern — `set -a; source .env; set +a` in bash is three lines and zero new dependencies. Adding `python-dotenv` would be a real dependency for a one-line problem.

- **No fix for exact-match brittleness against LLM verbosity.** The smoke output shows 3 of 5 questions scoring 0 because the LLM appends parentheticals to otherwise-correct short answers (e.g. `"Pale blue (with a film/veil over it)"` vs gold `"pale blue"`). The M5 README anticipates this; the proper fix is LLM-judge (B3), not more aggressive string normalisation.

## Observations

- **Two real harness bugs (PYTHONPATH-on-respawn, dropped resource fields) caught only because M7 is the first task that actually runs the full sequence.** Neither was caught by unit tests because tests use the stub SUT, not a real subprocess that depends on PYTHONPATH or reports tokens. This validates the M7 brief's framing of itself as "the natural place to surface seams." If the harness gains more tests in the post-MVP backlog, an integration test using the no-state SUT with a fixture API client (or even a hand-rolled fake `anthropic.Anthropic`) would catch this kind of bug earlier.

- **Anthropic 529 overloaded errors were sustained, not transient.** The SDK's default `max_retries=2` with exponential backoff didn't ride them out. A real benchmark deployment will need either provider-side retry budgets or a multi-provider fallback. B9 covers part of this.

- **The smoke result is exactly the expected null result.** The no-state SUT is the floor — no learning, no retention signal, all questions excluded by `C≈P`. This is a good thing: it means the *scorer* correctly identifies "no signal here" rather than spuriously generating a curve. The first non-trivial retention curve will require B1 (notes-LLM SUT) or B2 (naive-RAG SUT).

- **The static-vs-actual `model_id` issue was surfaced by switching models.** If we'd stayed on Haiku, this seam wouldn't have shown up until much later. Worth keeping in mind: configuration overrides that bypass the manifest are a class of audit-trail bug, and the fix (SUT reports actual values, harness writes through) generalises.

- **`anthropic` package install required `--break-system-packages`.** Dev container is shared Python; PEP 668 marks system-managed. Existing convention in this repo (per M4 debrief: pyproject's `[project.optional-dependencies]`) presumes a venv, but the dev container doesn't have one. Not a blocker; documented inline.

## Follow-ups

### Filed as tasks

- **B9 — Generic LLM-backend abstraction** (added to `TASKS.md` backlog). OpenRouter or pydantic-ai style provider-neutral client. Decouples reference-SUT code from any one provider's SDK. Direct lineage from the Haiku-overloaded experience today.

### Considered and dropped

- **`runs/latest` symlink.** Would be ergonomic for ad-hoc CLI use but adds a new harness side-effect for a problem the wrapper already solves. Could revisit if a real user workflow needs it.

- **Retry/backoff in the no-state SUT for 529s.** The SDK already has built-in retries; sustained 529s aren't a code problem, they're a capacity problem. The right fix is multi-provider fallback (B9), not provider-specific retries.

- **Integration test using a fake-anthropic-client and the real no-state SUT subprocess.** Would have caught both M7-discovered bugs earlier. Genuine value, but adds non-trivial test infrastructure (subprocess management, fake SDK) and is post-MVP polish. Revisit when CI / continuous testing becomes a real concern.

- **A separate `--model` flag on the no-state SUT or `run.sh smoke`.** `NO_STATE_MODEL` env var already exists; adding a flag is duplicate plumbing. The env-var path also persists nicely in `.env`.

- **Patching `harness/__main__.py` to surface the resolved model_id back to stdout** so users see "running against claude-sonnet-4-6" at start. Nice-to-have, not load-bearing — `sut-manifest.json::resource_appendix.model_id` records it definitively.

- **Adding `python-dotenv` as a dependency.** See Design decisions.

### Drive-by cleanup landed

- `.gitignore` now excludes `.env` / `.env.*` (with `.env.example` allow-list). Landed in the same M7 work commit.
