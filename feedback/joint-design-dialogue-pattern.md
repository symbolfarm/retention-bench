---
title: Design-dialogue + idea-tree pattern for upstream-of-plan scoping
status: open
raised: 2026-05-06
raised_by: Toby + Claude (CNN scoping session)
---

## Context

`plan.md` is a *commitment* artifact — by the time it exists, the
high-abstraction joint exploration phase is over. The CNN project
scoping session surfaced a real gap: there's no artifact for the
phase *before* `plan.md`, where Toby and Claude jointly converge on
what research question is actually being answered, before any branch
or experiment is committed to.

Two artifacts emerged from that session and earned their keep within
one conversation:

1. **`design-dialogue.md`** — turn-by-turn record of the
   high-abstraction conversation. Each turn dated, with explicit
   echo-backs, surfaced ambiguities, and `PENDING CONFIRMATION`
   markers when reframes are large. Captures *how* an alignment was
   reached, not just *that* it was reached.

2. **`idea-tree.md`** — navigable branching map of the project's
   ideas, with per-branch status badges (`#proposed` / `#exploring` /
   etc., reusing the skill's status vocabulary). Has a screen-fit
   tree-at-a-glance, a dimensions section listing orthogonal axes,
   and a per-branch section. A real experiment is a *tuple over the
   axes*. Branches promote into a variation-set + `plan.md` when they
   reach `#exploring`.

Both used Obsidian-compatible markdown (wiki-links, status tags) so
Toby could navigate visually.

## Update 2026-05-06 (post-scaffolding feedback from Toby)

After the CNN scaffolding, Toby flagged that the **design-dialogue
file is the wrong shape** even though the *substance* it captured
was valuable. Specifically:

- He's unlikely to come back to a turn-by-turn dialogue file.
- The valuable content — decisions, clarifications, misinterpretations
  — should land in the navigable idea-tree, not be buried in a
  monolithic file (even one with a top summary).
- A per-turn audit trail isn't worth its bookkeeping cost.

So the two-artifact pattern collapses to **one durable artifact**
(the idea-tree) plus an in-conversation discipline of distilling
each turn's substance into the tree as it happens.

## Proposal / decision (revised)

Add to `forward-research-conventions.md`:

- **`idea-tree.md` is the durable scoping artifact.** Single file,
  Obsidian-compatible, navigable, status-tagged per branch.
- **Per-branch sections include `## Decisions`, `## Clarifications`,
  `## Misreadings caught`** subsections — substantive content from
  joint scoping lands here, scoped to the branch it relates to.
- **A top-level `## Cross-cutting decisions`** section captures
  resolutions that don't belong to a single branch.
- **No separate `design-dialogue.md`.** The conversation happens
  inline in chat; the discipline is distilling each turn's substance
  into the tree before moving on. The chat history is the audit
  trail; the tree is the record.
- **Echo-back / ranked-options / length-budget norms** still apply
  (see `echo-back-communication-norms.md`) — those are about *how*
  the conversation runs, independent of artifact shape.

CNN's existing `design-dialogue.md` stays in place as audit trail
for the scoping that produced this lesson, but does not establish
a precedent for future projects.

Status `open` until exercised on a second project with the revised
shape. If the no-dialogue-file approach earns its keep, land it.
