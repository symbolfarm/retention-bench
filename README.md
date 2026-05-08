---
title: Continual-Learning Eval (CL-N)
status: scoping (joint-scoping mode; pilot #2 of the joint-scoping pattern)
started: 2026-05-08
promoted_from: scratch/continual-learning-eval/ (commit 3733126)
tags: [project, continual-learning, eval, benchmark, scoping]
---

# Continual-Learning Eval

Research project for a benchmark that measures **how gracefully a system's task performance degrades across discontinuities** that erase working state. The headline artifact is a *retention curve*: task score as a function of the number of discontinuities, comparing systems with different memory/state-preservation strategies on equal footing.

Two tracks are in scope:

- **Agent-memory track** — SUT is an LLM agent with a persistent filesystem; "discontinuity" is a process restart. Existing v0.1 spec ([[spec]]) is largely about this track. **Externally-legible track** — most readers will land here first, since most current memory-system work is in this regime.
- **Weight-update / constructive track** — SUT is a model + training/construction procedure; "discontinuity" is a weight update or a structural growth event. Currently lives as a deferred extension in [[extensions]]. **Priority track for this project's owner** — the constructive-neural-networks project depends on this evaluator existing.

Scoping decisions resolve the way constructive-track concerns dictate, but the agent-memory track keeps its seat at the table because (a) it's the more externally legible framing and (b) v0.1 of the spec already invested heavily in it.

## Entry points

- [[spec]] — the existing v0.1 design spec, promoted from `scratch/`. Effectively the agent-memory track in current form. **Read for the protocol shape, not as a final commitment to scope.**
- [[design-dialogue]] — joint-scoping conversation. Turn 1 reopens the v1-vs-extension scoping question and surfaces the two-track reframing.
- [[handover]] — short read-order guide for a fresh Claude resuming this project.

The other 7 spec documents (`protocol.md`, `interface.md`, `metrics.md`, `tasks.md`, `topology.md`, `validity.md`, `extensions.md`, `open-questions.md`) are reference material under joint-scoping treatment — they are *v0.1 starting points*, not stable specifications.

## What this project owes other projects

- **constructive-neural-networks** depends on the weight-update track existing in some form. CNN's branch-promotion gate ("read the eval before drilling into target signal or unit-of-construction") was set against this project's previous shape (a deferred extension); promoting + reopening scope satisfies the dependency-shape that CNN actually needs.

## Communication norms

This project uses the **echo-back / design-dialogue / idea-tree** joint-scoping pattern, same as the CNN project. See `feedback/joint-design-dialogue-pattern.md` and `feedback/echo-back-communication-norms.md`. The CNN project is pilot #1 of this mode; this is pilot #2.

## Status

Scoping. No `plan.md`. The first joint-scoping question is **whether the eval is one protocol with two tracks, or one protocol with one headline track and an extension family** — see [[design-dialogue]] Turn 1.
