# Debrief: RB-22 Retire the orphan-`main` split; move to a standard tag-based release

**Completed:** 2026-08-08
**Commits:** `5a2f692` (release-process retirement), `ccb1011` (public framing pass),
`88cb4c2` (uv trap + release notes) — tagged `v0.1.0`

## Design decisions

**The orphan `main` was renamed aside, not deleted.** `archive/orphan-main-v0.1` still exists
on the remote and is publicly visible. The brief offered either option; keeping it costs
nothing and it is the only record of what the project published under the old model. Note it
has *disjoint* history from `main`, so it will look strange to anyone browsing branches — that
is expected, not corruption.

**History was NOT rewritten.** The brief left this to Toby and it went the conservative way, on
measurements rather than instinct: the redacted address blob enters at `f802653` and leaves at
`ff5217b`, so **139 of 214 commits carried it**. A rewrite would renumber everything from
mid-May onward, invalidating 52 SHA fields in `LOG.jsonl` and hex references across ~59
markdown/jsonl files. `git filter-repo` emits a commit-map so remapping is scriptable, but any
missed reference becomes a dead SHA in a *public* repo. Against that, the address is published
on the authors' own paper, so marginal exposure is ~0. **This is now irreversible in practice**
— the history is public. Do not re-open it.

**`RELEASING.md` was rewritten, not amended.** Its old rationale argued for structural
concealment the repo no longer provides and would have been read publicly. The rewrite adds
something the original lacked: **version semantics tied to the measurement contract** — anything
that changes what an existing published number *means* is at minimum a minor bump. For an
instrument whose value is that a number is checkable, that matters more than the tagging
mechanics.

**The clean-checkout step became a real gate.** The old step 4 said "ideally run pytest". It now
requires that `./run.sh ladder` match `docs/reference-ladder.md` *exactly*, and blocks the
release on mismatch. This is the only gate that catches "the docs and the metric have drifted
apart", which CI cannot see.

**ROADMAP: amendment block → full prune.** First attempt added a dated amendment preamble on the
theory that editing a timestamped artifact weakens it. Toby pushed back correctly: that argument
only applies *after* publication, and under single-`main`-plus-tags the git history is the
timestamp anyway. The amendments were folded into the body and the block deleted. **Generalisable
lesson: the publication model changed what "timestamped" means, and the doc convention should
have followed automatically.**

**ADUS section cut 58 → ~20 lines** after discovering it was near-total duplication of
`notebook/notes/adus-mapping.md`, which is more detailed. Check the notebook before preserving
ROADMAP prose.

## Descoped / deferred

**Nothing from the brief.** All checklist items landed. Two items resolved differently than
written:

- "Confirm the ADUS reference points at something public" — the reference was to
  `github.com/symbolfarm/intelligence`, **a repo that never existed**. It came from an earlier
  LLM-drafted tech report and was absorbed as fact. Link removed rather than confirmed. Toby may
  create `adus-intelligence` / `adus-harness` later; nothing here needs to name them until they
  exist.
- "Add the CI badge / ensure CI runs on main and PRs" — CI already triggered on all pushes and
  PRs. Only the badge was missing.

## Observations

**`uv pip install -e` rejects git URLs outright** ("Editable must refer to a local directory").
The README's step 2 is a git URL and the pin *must* be editable (as a wheel, cl-benchmark
silently drops its task data files and every task construction fails). So uv users hit a hard
failure on the documented install path. Workaround documented in the README: `uv pip install
pip`, then `python -m pip install -e "git+..."`. **Worth re-checking on uv upgrades** — if uv
ever supports editable git URLs, the note should go.

**cl-benchmark's import path is `src`, not `cl_benchmark`.** `retention_bench/_clbench.py` is
the single chokepoint that hides this. Don't `import cl_benchmark` when smoke-testing an install.

**The reference ladder reproduces bit-exactly** from a fresh clone + fresh 3.13 venv, verified
twice (local clone at `ccb1011`, public clone at `88cb4c2`). All five rungs match
`docs/reference-ladder.md`. This is worth re-running as the gate for every future release rather
than trusting CI, which does not run the ladder.

**Watch for stale checkouts on the archive branch.** After the rename, a local clone was left
sitting on `archive/orphan-main-v0.1` and its working tree looked like a mass revert of docs.
Nothing was wrong. If files appear to have reverted, check `git rev-parse --abbrev-ref HEAD`
first.

**Newly public and deliberately kept:** `feedback/`, `history/`, `notebook/`, `scratch/`,
`docs/archive/`, `docs/reviews/`. `feedback/` and `history/` describe Toby's working patterns
rather than the instrument; he reviewed and chose to keep them. Do not quietly remove them.

## Follow-ups

### Filed as tasks

- **RB-23** Post-release consistency sweep — the ROADMAP's `Status` section, the README's "no
  language model has been measured yet", and `docs/reference-ladder.md` all encode a moment in
  time that RB-19 will invalidate. They should move together, and a released tag means they now
  drift *publicly*.

### Drive-by cleanup landed

- Four broken `./metrics.md` links in `docs/archive/` repointed to `../metrics.md` (`ccb1011`).
- `NOTICE` still listed "a constructive / parametric system class" as an original contribution;
  corrected to the mechanism-agnostic contract (`ccb1011`).
- `compression → re-representation` correction propagated through README, ROADMAP and both
  affected notebook notes, with a dated correction block in the ground-floor note (`ccb1011`).
  Raised by Toby: lossy, compressive and structured are three different things, and "compression
  forces structure" was in tension with the project's own expanding-memory claim.

### Considered and dropped

- Adding a per-file archive-notice header to `docs/archive/`. The supersession note in
  `docs/README.md` with an explicit precedence rule covers it, and per-file headers on 19 files
  would rot independently.
- Rewriting the ADUS material into a fuller ROADMAP section. It duplicates the notebook note;
  the pointer is the right shape.
