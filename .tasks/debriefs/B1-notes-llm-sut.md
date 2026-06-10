# Debrief: B1 Notes-LLM reference SUT

**Completed:** 2026-05-25
**Commit:** a0b501f

## What shipped

Second reference SUT under `suts/notes_llm/`, mirroring the `no_state/`
package shape. First SUT to use `DIR` for cross-`RESET` persistence and the
first that can produce a non-flat retention curve.

- `suts/notes_llm/{sut-manifest.json,pyproject.toml,README.md,notes_llm/__main__.py}`
  — `mode=in-context`, `strict_verbatim=false`, `entrypoint=["python","-m","notes_llm"]`,
  env `ANTHROPIC_API_KEY` + `NOTES_LLM_MODEL` (default `claude-haiku-4-5-20251001`,
  same default as no-state so the curve isolates notes value, not model swap).
- **READ:** single LLM call with prior notes + chapter, system prompt asks for
  a revised cumulative notes file wrapped in `<NOTES>…</NOTES>`. SUT parses
  the tags and atomic-writes `DIR/notes.md` (write to `.tmp` then
  `os.replace`).
- **QUIZ:** single LLM call with notes + questions only — no chapter text, no
  prior QUIZ history. Model emits `<ANSWER id="…">` per question; SUT parses
  into structured `answers` list per `docs/sut-interface.md`. Resource fields
  (`tokens_in/out`, `api_call_count`, `model_id`) emitted on both READ and
  QUIZ replies.
- `tests/fixtures/two_chapter.yaml` — 2 READs, 1 RESET, ceiling + k=1
  retention QUIZ. One question per chapter so cumulative-notes path is
  load-bearing.
- `tests/fixtures/fake_anthropic_notes_llm_responses.yaml` — 4 canned
  responses with distinct prime-ish token counts, full retention path.
- `tests/test_notes_llm_fake_anthropic.py` — drives real harness + real
  notes_llm SUT through the B10 fake-anthropic shim. Asserts trace shape,
  `sut_invocation_count=2`, shim counter advanced to 4, exact aggregate
  token totals across the RESET boundary AND across READ events, full
  retention on both questions, and `notes.md` mentions material from both
  chapters.
- **Harness patch:** factored
  `harness/event_loop.py::_accumulate_resources()` and call from both
  `_run_read` and `_run_quiz`. Previously only QUIZ replies aggregated
  SUT-reported resource fields; notes-LLM makes LLM calls on READ too, so
  READ-side tokens were silently dropped.

Suite: 42 passed, 1 skipped (live-API).

## Descoped / deferred

Nothing dropped from the brief. Explicit out-of-scope items (B2 naive-RAG,
B3 LLM-judge, agentic tool-use loop, per-call model config, hard size
budget, B9 LLM-backend abstraction) remain out of scope as planned.

## Design decisions

- **Atomic notes write (`tmp` + `os.replace`).** Not in the brief; added
  to avoid a half-written `notes.md` if the SUT is killed (`RESET` or
  crash) mid-write. Per `docs/sut-interface.md`, "anything that needs to
  survive a `RESET` must already be on disk before the response that
  preceded the `RESET` was written." A non-atomic write could corrupt
  the file even pre-`RESET` if the harness times out mid-flush. One-line
  cost; load-bearing for audit-trail integrity.

- **Tag-parsing fallback for `<NOTES>`.** If the model forgets tags, the
  SUT writes the whole reply as notes rather than blanking the file.
  Asymmetric cost — losing the file loses all retention signal; carrying
  a sloppy reply just produces a noisier-than-ideal data point. Errs
  toward preserving signal. Same fallback is NOT applied for `<ANSWER>`
  on QUIZ: there the structured list is the contract surface, and an
  unparsed reply correctly shows up as "missing answers" (recorded as
  `not_found` per question) rather than silently misclassified content.

- **Same prompt shape on first READ as on subsequent READs.** First READ
  shows `<PRIOR_NOTES>` block with placeholder text `"(no prior notes
  yet — this is the first chapter)"`. Considered branching to a separate
  "first-read" prompt with no prior-notes section; rejected because the
  uniform prompt is simpler and the placeholder is unambiguous. Avoids a
  two-prompt maintenance burden.

- **Harness patch landed in the B1 commit, not filed as follow-up.** Same
  rationale as the M7 in-task patches: small (<20 LOC, one new helper),
  fixes a concrete blocker for the B1 acceptance criteria (resource
  fields on every LLM-using event reply), doesn't change any locked
  contract, and is in the same logical change as the SUT that surfaced
  it. The bug is identical in class to the M7 dropped-resource-fields
  regression that B10 protects against — this just widens the contract
  from "QUIZ only" to "every event reply that may carry self-report."

- **No fix to `no_state` for the (now-fixed) READ-resource path.** The
  no-state SUT doesn't make LLM calls on READ — it returns an empty
  `stage_output` — so its READ replies have nothing to report. No change
  needed.

- **Test asserts `notes.md` content (`"Mira Vexin"` + `"Halton Reeve"`).**
  Substring assertions, not exact-file match, because the fake's canned
  notes content can be tuned later without breaking the test as long as
  it preserves the key facts. The test is about the *path* (cumulative
  notes survive RESET on disk and drive correct answers), not about the
  exact note format.

- **READ #1 placeholder string.** `"(no prior notes yet — this is the
  first chapter)"` — added to the prompt so the model gets a clear
  signal about being on chapter 1 without needing prompt-level branching.
  Surface detail; mentioned only because it's user-facing-ish (it ends
  up in the trace's `stage_input_path`).

## Observations

- **B1 surfaced a real harness bug on first run.** The integration test
  failed with `268 == 580` on token aggregation — exactly the wrong
  proportion (4 LLM calls reported, only 2 QUIZ calls aggregated). This
  is the *third* time a new task has surfaced a harness-side
  resource-accounting gap (M7 found the dropped-on-QUIZ bug + the
  PYTHONPATH-on-respawn bug; B1 found dropped-on-READ). The pattern is:
  the harness's resource-accounting code path is only exercised when a
  new SUT makes calls in a previously-unexercised event slot. Worth
  keeping in mind — the next time we add a SUT or event type, assume
  the accounting needs widening until proven otherwise.

- **B10's shim pattern transferred trivially.** New test file is ~110
  lines, structurally identical to `test_no_state_fake_anthropic.py`.
  The shim itself needed zero changes — its surface is small enough
  that swapping fixtures + counter paths is all that's needed for a
  new SUT. Confirms B10's "considered and dropped" judgment about not
  generalising the shim into a `fake_*` family was right: duplicating
  is fine.

- **Full retention is achievable with the fake.** The test asserts both
  questions correct after RESET because the fake faithfully reproduces
  notes-derived answers. Real notes-LLM against Haiku probably won't
  get full retention on real material — that's the point of a real
  curve. The integration test isn't measuring SUT quality; it's
  measuring that the *path* from notes → answers across RESET is wired
  correctly.

- **`run_dir / "dir"` is the canonical DIR path.** Confirmed via
  `harness/dir_lifecycle.py:31`. `--keep-dir` is not a flag — the
  default is to keep, and `--cleanup-dir` opts in to deletion. (I had
  this wrong on first pass; fixed before commit.)

- **Protocol drift caught + corrected.** B1's LOG.jsonl entry was added
  as `in_progress` before the task file was committed (visible from
  the session-start git status with `?? .tasks/B1-notes-llm-sut.md`).
  Reverted to `pending`, committed as `chore: file B1 …`, then flipped
  to `in_progress`, then ran the work. Worth noting if it happens
  again — the task-cycle skill doesn't currently call out the
  file-task-before-flipping-status ordering explicitly, though it's
  implicit in the "Starting a task" sequence.

## Follow-ups

### Filed as tasks

None. Real curves on a real task will surface the next batch
(`docs/sut-interface.md` improvements, judge-scorer integration B3,
naive-RAG B2, etc.) — all already in TASKS.md backlog.

### Considered and dropped

- **Adding a `READ`-event resource-accounting unit test using the stub
  SUT.** The new `test_notes_llm_fake_anthropic.py` is a regression
  test for the same bug, and is integration-level. A pure unit test
  on the stub SUT would be cheaper but duplicates coverage; skip
  unless we hit a second READ-accounting bug.

- **Patching the task-cycle skill to call out the
  "file-before-in_progress" ordering rule explicitly.** The skill
  already implies it (`.md` file written + LOG entry appended in
  "Starting a task" step 3-4). I could open a meta-task to clarify
  the docs, but a single occurrence isn't enough signal to justify
  the churn. If it happens again, file.

- **A "first-read" prompt variant without the `<PRIOR_NOTES>` block.**
  Marginal prompt-engineering improvement; rejected as not worth the
  maintenance cost (two prompts to keep in sync). If the model is
  visibly confused by the placeholder, revisit.

- **Adding a hard size cap on notes.md.** Brief explicitly defers this;
  the advisory ~2000-token limit in the system prompt is the lever
  for now. If notes blow up on real material, the trace will show
  it (notes-file size is implicitly recorded via the post-run DIR
  snapshot in `dir-snapshot.tar.gz`).

- **`run.sh notes-llm` wrapper (analogous to `run.sh smoke`).** Not
  needed yet — there's no notes-LLM-specific task definition to
  drive. When B1 first runs against a real task (e.g. the cohort-1
  novella), revisit then.

### Drive-by cleanup landed

None.
