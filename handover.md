---
title: Handover — continual-learning-eval (post-Turn-3)
project: continual-learning-eval
date: 2026-05-09
from: Claude (scoping session, Turns 2-3)
to: a fresh Claude resuming this project
tags: [handover, scoping]
---

# Handover — continual-learning-eval, post-Turn-3

## Where the project is

**Phase**: scoping. Joint-scoping mode (pilot #2). Project promoted
from `scratch/continual-learning-eval/` on 2026-05-08 (commit 3733126,
unedited). The 9 v0.1 spec docs are reference material under
joint-scoping treatment, not stable specifications.

**State as of Turn 3 (2026-05-09):** the SUT interface is now defined
to be **mechanism-agnostic** — one protocol, one five-thing contract
(STAGE_INPUT, STAGE_OUTPUT, persistent-state directory, action budget,
optional clear schedule + awareness flag), and SGD / structural growth
/ agent-notes / vector-store / EWC are all *reference modes* above the
interface rather than separate protocol tracks. The "two tracks" frame
from Turn 1 has softened to "two areas of focus" for task and
reference-mode design.

## Read order for a fresh Claude

1. [[README]] — project overview.
2. [[design-dialogue]] — **read all three turns, in order.** Turn 3
   has the canonical worked sketch (harness loop + SUT-type table)
   and the eight cumulative "Agreed" markers. **Read before doing any
   other work on this project.**
3. [[spec]] — v0.1 design overview. Treat as reference, not spec.
4. [[interface]] — v0.1 six-thing contract; **superseded by Turn 3's
   five-thing agnostic contract**, but useful for the design history.
   Slated for rewrite.
5. [[extensions]] — v0.1 deferred extensions; the
   *Weight-update / catastrophic-forgetting CL* section is **partially
   dissolved** (those algorithms become reference modes, not a
   separate track). Other extensions (failure-mode diagnostics,
   multi-agent, adversarial, etc.) still stand. Slated for rewrite.
6. The other 5 v0.1 docs — read on demand.
7. [[../constructive-neural-networks/handover]] — context on the
   downstream project that depends on this evaluator existing.

## What is *not* yet decided

- **Turn 4's direction.** Three ranked options pending Toby's pick:
  (1) pressure-test the unified interface with one real task from
  [[tasks]] walked through ≥2 SUT types (Claude's pick),
  (2) rewrite [[interface]] directly from Turn 3's sketch,
  (3) sketch constructive-area reference modes.
- **`interface.md` rewrite.** Needed to match the five-thing agnostic
  contract; not done yet.
- **`extensions.md` rewrite.** The *Weight-update / catastrophic-
  forgetting CL* section needs revising now that it partially
  dissolves into reference modes.
- **Whether "CL-N" survives** as the eval's overall name. Deferred.
- **Constructive-area reference modes.** Sketch list exists in Turn
  3's table (no-state baseline, naive checkpoint-and-grow, etc.) but
  not designed.

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

- [[../constructive-neural-networks/]] — downstream project. CNN's
  `idea-tree.md` already points at this project's directory (verified
  2026-05-11).
