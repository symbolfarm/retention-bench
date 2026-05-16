---
title: Echo-back communication norms for joint scoping with Toby
status: open
raised: 2026-05-06
raised_by: Toby + Claude (CNN scoping session)
---

## Context

The CNN scoping session surfaced that **bidirectional ambiguity** is
the failure mode the joint-scoping phase needs to design against.
Toby's plain-language research statements often have multiple
plausible interpretations that don't fully crystallise until an
implementation attempt; Claude's natural mode (expanding on the first
plausible reading) makes this worse.

Toby is also the bandwidth bottleneck — Claude reads/writes ~10x
faster, so the workflow has to be designed for Toby scanning, not
Claude producing. A "menu of 7 options" is the bottleneck-creating
move; a "ranked 3, with my pick + reason" is one decision.

The norms below were converged on during that session and earned
their keep across four turns of dialogue.

## Proposal / decision

Capture in `forward-research-conventions.md` (scoping-phase section,
alongside the design-dialogue/idea-tree artifacts):

- **Echo-back before elaboration.** When Toby states a non-trivial
  research idea, Claude's first move is to mirror it back as 2-3
  distinct interpretations and flag where Claude is guessing. Cheap
  to write, fast to scan, surfaces ambiguity before code is touched.
- **Ranked options + Claude's pick + reason.** Not a menu — a
  recommendation. One decision for Toby to ratify or override.
  Default cap: ≤3 options.
- **Length budget on Claude's side.** Echo-backs ≤5 lines. Long
  tables, ASCII trees, and ranked-option blocks are fine when they
  collapse complexity for fast scanning.
- **`PENDING CONFIRMATION` markers** in the design-dialogue when a
  large reframe lands. The dialogue commits the reframe to file
  immediately but flags it as not-yet-confirmed; the next turn
  confirms or corrects.
- **Concrete toy examples as the disambiguation tool.** Plain
  statements often only crystallise at implementation; the cheap
  version is a 5-line pseudocode sketch, a 4-row I/O table, or a
  mocked result item. Disambiguates without paying full
  implementation cost.

Status `open` until exercised on a second project. The norms should
also be persisted in Claude's auto-memory so they apply to any future
conversation, not just CNN.
