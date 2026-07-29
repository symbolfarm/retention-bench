# RB-17 — Reframe the README: research instrument, not benchmark

**Status:** completed 2026-07-29
**Commit:** `e864c97` (`docs: reframe the README as a research instrument, not a benchmark (RB-17)`)
**Touched:** `README.md`, `docs/README.md`. Docs only — no code, tests, or task behaviour.

## What shipped

`README.md` rewritten around the reframe:

- **Opening.** First sentence now calls it a *research instrument*; second
  paragraph glosses "bench" as **workbench**, states there is no leaderboard and no
  submission process, and links `docs/ROADMAP.md` plus an anchor to the new scope
  section. The CL-Bench extension framing follows rather than leads.
- **"The claim it exists to test."** New section carrying the thesis verbatim in
  spirit with `docs/ROADMAP.md`: storage is not memory; the operational difference
  is composition; in-context learning produces access without integration;
  retrieval is in-context learning with a bigger drawer.
- **"Why a hard RESET."** New section with the one-time-vs-recurring-cost argument
  and the explicit long-context rebuttal (reload from disk every session, pay for
  it every session). The mechanism-agnostic-interface paragraph, previously
  orphaned near the top, moved here where it actually reads as support.
- **Numbers re-checked against the post-RB-16 ladder.** The ladder paragraph now
  quotes the 112-instance default schedule, `r_max = 64/112 ≈ 0.571`, `k = 55` /
  `k = 111`, the rung values (`no_state` 0.000, `reset_lossy` 0.547 → 0.344,
  `bounded_memory` / `associative_memory` 1.000), and the chance line
  (`1/num_attributes = 1/16 = 0.0625` per probe, `0.0357` run-mean, `random_guess`
  measured 0.027).
- **Task knobs documented.** New short paragraph naming `num_attributes` /
  `objects_per_attribute` with the current defaults (16 / 2) and the
  `chance = 1/num_attributes` relation, linking `docs/associative-curriculum.md`.
- **"Scope and limits."** New honest section: one owned task (with the roadmap's
  unbuilt probe families named); the constructive-retention co-design hazard named
  and converted into pre-registration; no language model measured yet, so the
  central claim is unfalsified; cost metric unsettled; results are the authors'
  own and the keyless ladder is the reproducible part. Closes with "adoption
  follows an interesting result, not benchmark infrastructure."
- **Documentation section** promotes `docs/ROADMAP.md` to the first entry.

`docs/README.md` intro gained the instrument/workbench/no-leaderboard sentence and
a `ROADMAP.md` row at the top of the doc table.

## Design decisions made in-flight

- **Kept the ladder numbers in prose, not a table.** `docs/reference-ladder.md` is
  the source of truth and already tables them; duplicating the table in the README
  creates a second thing to keep in sync at every re-measurement. The README quotes
  the separating figures inline and points at the doc.
- **No reference-system *count* in the README.** `docs/ROADMAP.md` says the
  instrument has measured "four synthetic reference systems"; the ladder has five
  rungs (the fifth being `random_guess`, whose band is EXCLUDED by design and which
  is a calibration line rather than a retention system). Both readings are
  defensible, so the README says "keyless synthetic reference systems" without a
  number rather than contradicting the roadmap. **Flagged for the author:** if a
  count is wanted, pick one and make both documents say it.
- **Left `AGENTS.md` alone.** Its "What this repo is" paragraph still says
  "designing a benchmark" and its status section is frozen at 2026-05-20 (pre-pivot,
  pre-CL-Bench). It is agent-facing, not public, and out of the declared `Touches`
  set. Filed as a candidate below rather than swept in.
- **Left the `docs/README.md` history footnote's "began life as a standalone
  benchmark".** That is a historically accurate statement about the pre-pivot era,
  not a live claim.
- **Moved the "bring your own task" and `--task-spec` material unchanged.** It was
  already framed as third-party usage, which supports rather than undercuts the
  instrument framing.

## Verification

- Stale-figure grep across `README.md` + `docs/README.md` for `16/26`, `0.615`,
  `num_concepts`, `cap 8`, `rate 0.05`, `0.308`, `leaderboard`, `submission`,
  two-bin / red-blue-era wording: **clean**. The only surviving `leaderboard` /
  `submission` hits are the new sentences that explicitly deny both, and the only
  surviving `benchmark` hits are the workbench disclaimer, the `cl-benchmark`
  dependency name, the historical footnote, and "rather than benchmark
  infrastructure".
- All 30 unique relative links in both files resolve to existing paths (checked
  mechanically, anchors stripped). No dead links.
- `.venv/bin/python -m pytest` → **154 passed, 2 skipped**, unchanged.

## Candidate tasks surfaced

- **Real task:** `AGENTS.md` orientation refresh. It predates the CL-Bench pivot
  *and* the reframe: it describes the repo as "designing a benchmark", lists a
  read order full of archived/deleted docs (`docs/decisions-checklist.md`,
  `docs/tasks.md`, `docs/book-spec.md`, `history/`), and its "what is not yet
  decided" section is two pivots stale. A fresh agent reading it first would be
  actively misdirected. Not a drive-by — it needs a real rewrite pass.
- **Author decision (not a task):** reconcile the reference-system count between
  `docs/ROADMAP.md` ("four") and the five-rung ladder, per the note above.
