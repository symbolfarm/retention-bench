---
title: Handover — continual-learning-eval (initial scoping)
project: continual-learning-eval
date: 2026-05-08
from: Claude (scoping session)
to: a fresh Claude resuming this project
tags: [handover, scoping]
---

# Handover — continual-learning-eval, post-promotion

## Where the project is

**Phase**: scoping. Joint-scoping mode (pilot #2). Project promoted
from `scratch/continual-learning-eval/` on 2026-05-08 (commit 3733126,
unedited). The 9 v0.1 spec docs are now reference material under
joint-scoping treatment, not stable specifications. Turn 1 of the
design-dialogue lands the two-track reframing and asks Toby to pick
between three ranked next moves.

## Read order for a fresh Claude

1. [[README]] — project overview + the two-track framing.
2. [[design-dialogue]] — Turn 1 has the echo-back of v0.1 scope, the
   reframing, the four 2026-05-08 agreements, and three ranked
   options for Turn 2. **Read before doing any other work on this
   project.**
3. [[spec]] — the v0.1 design overview (what was `README.md` in
   scratch). Treat as reference, not as spec.
4. The other 7 v0.1 docs — read on demand. [[interface]] is the
   most likely first read because Turn 2 option #1 (Claude's pick)
   chases the interface-contract delta.
5. [[../constructive-neural-networks/handover]] — context on the
   downstream project that depends on this evaluator existing.

## What is *not* yet decided

- **Turn 2's direction.** Three ranked options pending Toby's pick:
  (1) interface-contract delta, (2) worked-example task, (3) open-
  questions triage. Claude's pick is #1.
- **Constructive-track name.** "Weight-update CL" is the inherited
  name from `extensions.md`; may not survive the two-track
  reframing.
- **Whether "CL-N" survives** as the eval's overall name now that
  it covers both tracks.
- **Constructive-track reference SUT design.** Defer until Turn 2
  or 3.

## Communication norms (important)

This project uses the **echo-back / design-dialogue / idea-tree**
joint-scoping pattern, same as constructive-neural-networks. See
`feedback/joint-design-dialogue-pattern.md` and
`feedback/echo-back-communication-norms.md`. The auto-memory entry
`feedback_joint_scoping_norms.md` covers this — should auto-load.

## Useful Toby-context for this project

- Toby is the **author of the v0.1 spec** (in `scratch/`). Don't
  treat the v0.1 docs as external work to be respected as-written;
  they're his own draft and he's actively reopening their scope.
- The eval is **early concept phase** by Toby's own framing — there
  is no audience or outside interest yet. Scoping decisions can be
  made on their merits without external constraints.
- **Constructive case is Toby's priority**; agent-memory case is the
  externally-legible framing. When tensions arise, constructive
  wins — but agent-memory stays in scope because it's where any
  external interest will land first.
- Toby is **not deeply familiar with the v1-vs-extension framing**
  in his own draft — this came up explicitly in the 2026-05-08
  scoping. Don't assume the v0.1 doc structure reflects strong
  prior commitments; treat distinctions as renegotiable.

## Cross-references

- [[../constructive-neural-networks/]] — downstream project. Idea-
  tree should be updated to point at this project's directory
  rather than `scratch/`.
