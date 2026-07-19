# Debrief: RB-14 Public-facing doc pass

**Completed:** 2026-07-19
**Commit:** 86e8d44

## What shipped

All four acceptance criteria, across 47 files:

- **Codename sweep**: every C*/B*/RB-* queue ID removed from public surfaces —
  shipped docstrings, test docstrings, SUT READMEs, Dockerfiles, docs/ — and
  replaced with plain-language descriptions. Verified by grep: zero residue on
  any `PUBLIC_PATHS` surface (`.tasks/` history keeps the IDs).
- **Dangling refs**: citations of the four archived spec docs and of `.tasks/`
  files reworded or repointed at "`docs/archive/` on the `dev` branch (not
  part of the public snapshot)".
- **Dev-path residue**: `_clbench.py`'s import error and `bsm_corpus.py`'s
  usage docstring no longer name the dev container's interpreter; the error
  now gives the generic editable-install instruction *with the reason*
  (cl-benchmark's wheel drops task data files).
- **Metric status marking**: `metrics.md` has a status-tag legend and every
  metric is tagged **[implemented]** or **[specified]** (with "recorded but
  not aggregated" called out where that's the honest state). Added the
  enforced-kill note (process-group SIGKILL + kill-on-timeout in subprocess
  mode; `docker rm -f` in container mode) per the brief.

Beyond the brief (small, review-driven):

- **README quickstart fixed**: added the editable cl-benchmark reinstall step.
  Without it a fresh `pip install -e .` user fails at `./run.sh smoke` with
  the same missing-data failure CI hit on 2026-07-19 — the quickstart was
  broken for real users, not just unpolished.
- **`docs/README.md`**: stale "constructive contract in progress" callout
  replaced (the development brief exists); table completed with
  `reference-ladder.md`, `phased-store-removal.md`, and the constructive
  brief; added a **"Repo tour"** suggested reading order (Toby's reviewer-
  guide request; equally aimed at C5's external readers).
- **`PUBLIC_PATHS`**: `!docs/reviews/` exclude added — internal review
  artifacts are dense with private-queue IDs and reference `.tasks/`
  debriefs; scrubbing them would destroy their value as historical records,
  so they stay dev-only instead. `promote.sh dryrun` verified clean.
- Test functions named `test_rb12_*` renamed to drop the codename.

Suite unchanged: 135 passed + 2 docker-gated skips.

## Descoped / deferred

Nothing from the brief. Metric *designs* untouched (per out-of-scope); C17
cutover not performed.

## Design decisions

- **Exclude `docs/reviews/` rather than scrub it.** The alternative (rewriting
  the v0.1 review in plain language) would falsify a dated historical
  artifact. Public readers get the *fixes*; the review stays readable on dev.
- **Codename→plain-language, not codename→deletion.** Where an ID carried real
  content ("C4 places resets on/off drift boundaries") the sentence keeps its
  meaning ("the drift experiments place..."); pure provenance tags were
  dropped. Dates like "decided 2026-05-30" were kept — dates are meaningful to
  external readers, queue IDs are not.
- **Status tags inline** (`[implemented]` / `[specified]` per bullet) rather
  than a separate status table — keeps the tag next to the claim it qualifies,
  so future metric additions can't drift from a remote table.
- The Reporting-format checklist now says specified-metric items "apply once
  those are implemented" instead of implying they exist today.

## Observations

- The README quickstart being *functionally* broken (not just cosmetically
  internal) was the surprise of the pass — same root cause as the CI failure
  fixed earlier today (cl-benchmark wheel drops package data). Until the
  upstream package-data PR (C7 candidate 3) lands, every install path must
  say "editable" explicitly.
- Non-Python public surfaces (SUT READMEs, Dockerfiles) were nearly missed by
  a `--include=*.py` grep; the final verification greps run over *all* files
  under the `PUBLIC_PATHS` includes. Worth repeating before C17.
- `promote.sh dryrun` reads the *committed* tree, so it validates excludes
  immediately but content only after commit — rerun it at C17 time.

## Follow-ups

### Considered and dropped

- Adding `.github/workflows/ci.yml` to `PUBLIC_PATHS` so the public repo has
  CI — deliberately left for C17 (the cutover decides what the public repo
  runs; the workflow references the editable-reinstall story which is now
  documented either way).
- A standalone `REVIEWING.md` — folded into `docs/README.md`'s repo tour
  instead; a second entry-point doc would drift.
