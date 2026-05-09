---
title: Continual-Learning Eval (CL-N)
status: scoping (joint-scoping mode; pilot #2 of the joint-scoping pattern)
started: 2026-05-08
promoted_from: scratch/continual-learning-eval/ (commit 3733126)
tags: [project, continual-learning, eval, benchmark, scoping]
---

# Continual-Learning Eval

Research project for a benchmark that measures **how gracefully a system's task performance degrades across discontinuities** that erase working state. The headline artifact is a *retention curve*: task score as a function of the number of discontinuities, comparing systems with different memory/state-preservation strategies on equal footing.

**Interface design (resolved 2026-05-09, Turn 3 of [[design-dialogue]]):** one protocol with a **mechanism-agnostic interface**. The SUT is a subprocess that reads `STAGE_INPUT`, possibly mutates a persistent-state directory, and writes `STAGE_OUTPUT` within an action budget. Discontinuity = `process.kill()` + only the directory survives. SGD fine-tuning, structural growth (constructive nets), agent-with-notes, vector-store retrieval, EWC, and so on are all *reference modes* above the interface — the harness can't tell them apart.

Two **areas of focus** for task and reference-mode design (not protocol bifurcations):

- **Agent-memory area** — externally-legible framing; most current memory-system work lives here, so most external interest will land here first.
- **Constructive area** — priority area for this project's owner; the constructive-neural-networks project depends on this evaluator existing.

Task and reference-mode design decisions resolve the way constructive-area concerns dictate, but the agent-memory area keeps its seat because (a) it's the more externally legible framing and (b) v0.1 of the spec already invested heavily in it.

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

Scoping. No `plan.md`. Through Turn 3 of [[design-dialogue]] (2026-05-09): two-track-vs-extension question resolved (one protocol, agnostic interface, modes above the interface). Open question for Turn 4: pressure-test the unified interface with one real task walked through ≥2 SUT types (Claude's pick), or rewrite [[interface]] directly, or sketch constructive-area reference modes.
