# Debrief: C14 Public README rewrite + .env.example

**Completed:** 2026-06-10
**Commit:** 1db3570

## What shipped

- **`README.md`** rewritten as a lean, accurate public face: frames
  retention-bench as a hard-RESET + constructive extension on top of CL-Bench
  (post-pivot), a working quickstart, a short "how retention is scored" section,
  and pointers only to public docs + LICENSE/NOTICE.
- **`.env.example`** documenting the real env vars (key, base URL, model
  overrides), matching the quickstart. `.gitignore` already whitelisted it.
- Removed all pre-pivot / internal content: the "Continual-Learning Eval (CL-N)"
  framing, the broken `ANTHROPIC_API_KEY`/`claude-haiku` quickstart, the
  "Communication norms" and "What this project owes other projects" sections, and
  every link to `history/` / `feedback/` / `design-dialogue`.

## Verified against code (not memory)

- Key: **`OPENROUTER_API_KEY`** — required; SUTs `_die` without it.
- Base URL: **`RETENTION_BENCH_BASE_URL`**, default `https://openrouter.ai/api/v1`.
- Model overrides: `NO_STATE_MODEL` / `NOTES_LLM_MODEL` / `NAIVE_RAG_MODEL`,
  default `deepseek/deepseek-v4-flash`; judge `RETENTION_BENCH_JUDGE_MODEL`,
  default `moonshotai/kimi-k2.6`.
- Entry point: `./run.sh smoke` drives `tasks/smoke-test/task.yaml` through
  `suts/no_state` and scores — confirmed in `run.sh`.
- Final `promote.sh dryrun`: README + .env.example land on `main`, leak check clean.

## Descoped / deferred

- Did not document the full CL-Bench-runner invocation path in the README — kept
  the quickstart to the verified `./run.sh smoke`, with `docs/` covering the
  adapter/runner path. Avoids publishing a flow I couldn't run end-to-end here.

## Design decisions

- **No divergent README** (the C13 refinement): the lean README is authored on
  `dev` and snapshotted to `main`; `AGENTS.md` (dev-only) keeps internal
  orientation.
- **Quickstart install = `pip install -e ".[no-state-sut]"`** and **Python 3.13+**
  stated up front — the `cl-benchmark` git dependency sets the 3.13 floor. Chose
  the documented editable-install path over hand-tuning minimal deps for the smoke
  subset, to match how the repo is actually set up (egg-info / editable install).
- README links the external CL-Bench GitHub + arXiv id directly, consistent with
  the C15 NOTICE, leading with the contribution (no priority claim).

## Observations

- Could not execute `./run.sh smoke` end-to-end here (needs an OpenRouter key +
  network), so the *install* line is documented-but-unrun; the `run.sh smoke`
  invocation itself is verified against the script. Worth a real smoke run on a
  keyed machine before the public flip (a natural part of C17's "clean checkout
  runs" check).

## Follow-ups

### Considered and dropped

- *Add CI / badges to the README* — premature for a 0.1 pre-publication artifact;
  no CI exists yet. Not filing.
