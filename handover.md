---
title: Handover — continual-learning-eval (post-Turn-4)
project: continual-learning-eval
date: 2026-05-11
from: Claude (scoping session, Turns 2-4)
to: a fresh Claude resuming this project
tags: [handover, scoping]
---

# Handover — continual-learning-eval, post-Turn-4

## Where the project is

**Phase**: scoping. Joint-scoping mode (pilot #2). Project promoted
from `scratch/continual-learning-eval/` on 2026-05-08 (commit 3733126,
unedited). The 9 v0.1 spec docs are reference material under
joint-scoping treatment, not stable specifications.

**State as of Turn 4 (2026-05-11):** the agnostic five-thing interface
from Turn 3 was **pressure-tested** with book-episodic Track 1 walked
through both a notes-LLM and a constructive-transformer SUT. The
interface held; two small frictions surfaced as PENDING CONFIRMATION
items (see below). The walkthrough's main signal is that
**reference-mode design for the constructive area is the next real
bottleneck** — until at least one runnable constructive-transformer
reference SUT exists, the eval can't compare it to anything.

**Important new context from Turn 4:** the constructive SUT target is a
**constructive transformer** (growth in attention / embeddings / MLPs
of a pre-trained reasoning LM), not a classical small-net constructive
learner. This dissolves the "representation gap" concern — text tasks
are not constructive-hostile. See memory entry
`project_constructive_transformers.md`.

## Read order for a fresh Claude

1. [[README]] — project overview.
2. [[design-dialogue]] — **read all four turns, in order.** Turn 3 has
   the canonical worked sketch (harness loop + SUT-type table) and
   the eight cumulative "Agreed" markers; Turn 4 has the book-episodic
   pressure-test walkthrough validating the interface and surfacing
   two PENDING CONFIRMATION items. **Read before doing any other work
   on this project.**
3. [[open-questions]] — re-triaged 2026-05-11 against the agnostic
   interface; Items 1 and 4 reframed, others survive as-written.
4. [[spec]] — v0.1 design overview. Treat as reference, not spec.
5. [[interface]] — v0.1 six-thing contract; **superseded by Turn 3's
   five-thing agnostic contract**, but useful for the design history.
   Slated for rewrite.
6. [[extensions]] — v0.1 deferred extensions; the
   *Weight-update / catastrophic-forgetting CL* section is **partially
   dissolved** (those algorithms become reference modes, not a
   separate track). Other extensions (failure-mode diagnostics,
   multi-agent, adversarial, etc.) still stand. Slated for rewrite.
7. The other 4 v0.1 docs — read on demand.
8. [[../constructive-neural-networks/handover]] — context on the
   downstream project that depends on this evaluator existing.

## What is *not* yet decided

- **Two PENDING CONFIRMATION items from Turn 4**, awaiting Toby:
  - *STAGE_INPUT internal structure for the book track* —
    proposal: `<TEXT>...</TEXT>` + `<QUESTIONS>...</QUESTIONS>`
    sections, so SUTs with different ingestion modes treat them
    uniformly.
  - *Harness deletes STAGE_INPUT / STAGE_META between stages* —
    no-re-reads enforcement is harness-level, not just task-level.
  - If confirmed, these become Agreed #9 and #10.
- **Turn 5's direction.** Three ranked options pending Toby's pick:
  (1) confirm PENDINGs, then reference-mode design for the
  constructive area (Claude's pick — Turn 4 surfaced this as the
  bottleneck);
  (2) rewrite [[interface]] and affected parts of [[extensions]]
  from the now-validated five-thing contract;
  (3) walk a second task (codebase) through the same two SUTs to
  triangulate.
- **`interface.md` rewrite.** Needed to match the five-thing agnostic
  contract; not done yet.
- **`extensions.md` rewrite.** The *Weight-update / catastrophic-
  forgetting CL* section needs revising now that it partially
  dissolves into reference modes.
- **Whether "CL-N" survives** as the eval's overall name. Deferred.
- **Constructive-area reference modes.** Sketch list exists in Turn
  3's table (no-state baseline, naive checkpoint-and-grow, etc.) but
  not designed. Now the Turn 5 priority.

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
