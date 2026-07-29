# RB-17 Reframe the README: research instrument, not benchmark

**Priority:** high
**Blocked by:** RB-16 (numbers quoted in the README change when the ladder is re-measured)
**Touches:** `README.md`, `docs/README.md`

## Context

From the 2026-07-29 pre-release discussion.

The repo has been drifting back toward presenting itself as a benchmark, which contradicts a
decision already taken: the **2026-06-07 CL-Bench pivot** narrowed retention-bench to a
*reset + constructive extension on top of Continual Learning Bench* and explicitly **dropped
the general memory leaderboard**. It is an instrument used by a research programme and shared
publicly — not a standalone benchmark seeking submissions.

The evidence agrees with the pivot decision: one owned task, co-designed with the system meant
to win it (constructive-retention); no external users; a cost metric that isn't settled; and a
roadmap of probe families that don't exist yet. Benchmarks are frozen, adopted, and comparable
across submitters. This is none of the three, and claiming otherwise buys leaderboard
maintenance burden in exchange for nothing.

The name stays `retention-bench` — renaming costs the repo URL, package name and every doc
reference, and "bench" reads acceptably as *workbench*. But that reading only works if the
README does the work explicitly. **Toby's decision, 2026-07-29.**

The thesis the README should lead with, as settled in that discussion:

> **Storage is not memory.** A system can have perfect access to every token it ever saw and
> still not know anything. In-context learning (and retrieval, which is in-context learning
> with a bigger drawer) produces *access* without *integration* — the facts are available for
> lookup but they don't compose the way learned knowledge composes.

And the justification for the hard RESET, which is the sharpest framing produced so far:
**RESET converts a one-time cost into a recurring one.** A long-context system can always
reload everything from disk after a restart — and then pays that re-read every session,
forever. Without resets the cost is amortised across a run and the difference hides; with
resets it becomes visible and measurable. The reset is not a handicap, it is the mechanism
that exposes the scaling difference.

## Goal

The README presents retention-bench as a research instrument and CL-Bench extension, leads
with the thesis, states scope limits honestly, and quotes only numbers that survive RB-16.

## Acceptance criteria

- [ ] Opening reframed: instrument/workbench + CL-Bench extension, not benchmark. No
      leaderboard or submission language anywhere.
- [ ] "bench" explicitly glossed as workbench early enough that the name doesn't mislead.
- [ ] Thesis stated up front (storage vs memory; access vs integration).
- [ ] RESET justified via the one-time-vs-recurring-cost argument, including the explicit
      long-context rebuttal ("reload from disk each session — and pay for it each session").
- [ ] Honest scope limits section: one owned task; co-designed with constructive-retention;
      no LLM systems measured yet as of this release; results are the authors' own.
- [ ] Every quoted number re-checked against the RB-16 re-measured ladder. No stale
      `16/26`-era figures.
- [ ] Links to the roadmap (RB-18) as the research agenda.
- [ ] `docs/README.md` repo tour (added by RB-14) stays consistent with the new framing.

## Relevant files

- `README.md` — the public face
- `docs/README.md` — repo tour, must not contradict the reframe
- `docs/reference-ladder.md` — source of the numbers quoted (post-RB-16)
- `TASKS.md` — the pivot decision text, for wording consistency

## Decisions already made

- **Keep the name `retention-bench`** (Toby, 2026-07-29) — renaming is expensive and "bench"
  as *workbench* is fine, provided the README says so.
- **Keep the dev/main orphan split** (Toby, 2026-07-29) — already cut by C17, costs nothing
  to retain, no change needed under the new framing.
- **Don't claim benchmark status and don't build toward it.** Adoption comes from an
  interesting result, not from benchmark infrastructure. The route is: get a striking result →
  people want to reproduce → *then* freeze and formalise.
- **State the co-design hazard rather than hide it.** RB and CR are developed together and CR
  is the system expected to do well. Naming that, plus publishing the roadmap before measuring
  CR on it (RB-18), converts the hazard into a pre-registration.

## Out of scope

- The roadmap document itself (RB-18).
- Any code change — this is docs only.
- Renaming the repo, package, or CLI.
