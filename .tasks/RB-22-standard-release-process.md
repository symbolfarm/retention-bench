# RB-22 Retire the orphan-`main` split; move to a standard tag-based release

**Priority:** high (blocks the public flip)
**Blocked by:** **TOBY — do not start.** Two decisions are his and are not
delegated: whether to rewrite git history before publishing (see Notes), and the
irreversible act of flipping repo visibility. Publishing is `third-party-contact`
/ irreversible class either way. An agent may *draft* the `RELEASING.md` rewrite
if explicitly asked for it; an agent may not delete branches, rename `dev`, change
the default branch, push tags, cut a release, or change repo visibility.
**Touches:** branch layout on GitHub, `RELEASING.md`, `scripts/promote.sh`,
`PUBLIC_PATHS`, `README.md`, `.github/workflows/ci.yml`, repo settings

## Context

The two-branch model (`dev` working + orphan `main` public face) was designed to
do two jobs: **conceal** the working history, and **curate** a small clean tree
for arriving readers. The 2026-08-05 decision to publish `dev` retires the first
job entirely, and with only curation left the split costs more than it returns:

- **Staleness became visible.** `main` is ~3 weeks behind `dev` — missing
  `docs/ROADMAP.md`, `docs/phased-store-removal.md` and the `random_guess` chance
  rung, and still shipping the retired `suts/constructive/`. While only `main` was
  public that was merely out of date; with both branches public it is two
  published versions of the truth, and the stale one is the default.
- **`main` has no CI, structurally.** `.github/` is not in `PUBLIC_PATHS`, so the
  public face carries `tests/` but has never run them. `RELEASING.md` step 4
  compensates with a manual clean-checkout run, which is exactly the kind of
  human step that gets skipped.
- **Disjoint history is hostile to contribution.** The README invites third
  parties to point the instrument at their own systems and to say it measures the
  wrong thing. Someone cloning the default branch gets a tree they cannot rebase
  onto `dev` or meaningfully PR against.
- **It is a polish tax** on a project that has explicitly decided to pay polish
  taxes only where they matter (AgentDesk), and to build in public otherwise.

Tags and GitHub Releases are the standard mechanism for "this exact tree produced
these numbers" — citable, immutable, and they work on a branch with real history
and working CI.

## Shape

One branch with real history, named `main`, with releases cut as tags.

## Checklist

**1. Pre-flight, while still private**

- [ ] Delete the stray remote agent branches: `claude/quirky-maxwell-hzz5r3`,
      `claude/continual-learning-benchmark-review-frrotp`.
- [x] **DECIDED 2026-08-07 (Toby): do not rewrite history.** The tree-level C5
      redaction stands. Measured cost of the alternative: the blob enters at
      `f802653` and leaves at `ff5217b`, so **139 of 214 commits carry it** — a
      rewrite renumbers everything from mid-May on, invalidating 52 SHA fields in
      `.tasks/LOG.jsonl` and hex references across ~59 markdown/jsonl files.
      `git filter-repo` emits a commit-map so remapping is scriptable, but any
      missed reference becomes a dead SHA in a public repo. Against that: the
      address is published on the authors' own paper (marginal exposure ~0), and
      the outreach-strategy phrasing reads as deliberate, not discreditable.
- [x] **DONE 2026-08-08.** The ADUS reference pointed at `symbolfarm/intelligence`,
      **a repo that does not exist** — it came from an earlier LLM-drafted tech
      report and was never followed through. Link removed; the section now says the
      framework is not yet gathered into a citable form. Toby intends
      `adus-intelligence` (theory) + `adus-harness` (implementation) later; nothing
      in retention-bench needs to name them until they exist.
- [ ] Re-run the credential scan on the full tree (last run 2026-08-05: clean; no
      key material tracked, `.env` never committed and correctly ignored).

**2. Branch cutover**

- [ ] Lift the branch ruleset (currently *no delete, no force push*) long enough to
      remove the orphan `main`, or rename it aside (e.g. `archive/orphan-main-v0.1`)
      rather than deleting.
- [ ] Rename `dev` → `main`; set it as the default branch.
- [ ] Re-apply the ruleset to the new `main`.
- [ ] Update any local clones and the `SRC=` habits in scripts/docs.

**3. Release mechanics**

- [ ] Retire `scripts/promote.sh` and the whitelist model. `PUBLIC_PATHS` becomes
      unnecessary — the invariant is no longer "these paths are safe to show" but
      "nothing in the repo is unpublishable", which is already true.
- [ ] Rewrite `RELEASING.md` as a short tag-based procedure: land on `main`, CI
      green, clean-checkout test run, `git tag v0.1`, GitHub Release with notes.
      **Its current rationale must go** — it argues for structural concealment the
      repo no longer provides, and it will be read publicly.
- [ ] Ensure CI runs on `main` and on PRs, and add the badge to `README.md`.
- [ ] Cut `v0.1` from the tree that the release post links to.

**4. Follow-through**

- [ ] Move `docs/archive/` and `docs/reviews/` decisions: they were dev-only under
      the whitelist and are now simply public. Confirm that is intended (the four
      broken `./metrics.md` links in `docs/archive/` become publicly visible rot —
      fix or add an archive-notice header).
- [ ] Update `AGENTS.md`: the branch model, the "public files are edited on `dev`"
      rule, and the promote step all change.

## Acceptance

- One branch, `main`, default, with the full working history and green CI.
- `v0.1` exists as a tag and a GitHub Release, and is what the announcement links.
- No document in the repo describes a branch model the repo does not have.
- `git clone && pytest` works from a clean checkout on the default branch.

## Notes

**On history rewriting.** The case for leaving it alone: the address is published
on the authors' own paper, so the marginal exposure is near zero, and rewriting a
history that agent sessions and `.tasks/LOG.jsonl` reference by SHA has its own
cost. The case for rewriting: it is free *now* and impossible later, and the
commits also contain the outreach-strategy phrasing that reads worse than the
address does. Recommendation is to leave it and let the tree-level redaction
stand, but it should be a decision rather than an oversight.

**What is genuinely lost:** the clean landing page. A good README buys back most of
it, and the honest signal of a research instrument whose notebook, task queue and
negative results are all visible is worth more than a tidy file list to the
audience this is for.
