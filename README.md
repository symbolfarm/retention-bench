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

**Eval philosophy (locked Turn 5, 2026-05-13):** the load-bearing rule is **cross-reset purity** — no scored question is answerable from the SUT's current `STAGE_INPUT` alone; every scored retention question requires state carried across at least one RESET. A run is a sequence of `READ`, `QUIZ`, and `RESET` events; a SUT process spans `RESET`-to-`RESET`. Per-question, the eval measures three probes: `P` (prior knowledge, before any reading), `C` (capability ceiling, with the text fresh in the same process), and `R(k)` (retention after `k` resets). The headline metric is **normalized retention** `(R − P) / (C − P)` — how much of what was *learnable in principle* survived the resets. A useful side-effect: pretraining contamination becomes a measured quantity (a high `P`) rather than something to be avoided, which widens the usable asset pool.

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

Scoping. No `plan.md`. Through Turn 5 of [[design-dialogue]] (2026-05-13): the agnostic five-thing interface (Turn 3) survived a book-episodic pressure-test in Turn 4. Turn 5 extended the design with the **atomic-event model** (`READ` / `QUIZ` / `RESET` events) and the **three-probe baselines** (prior / ceiling / retention), locking cross-reset purity as the eval's load-bearing rule (Agreed #9–#12 in [[design-dialogue]]). v0.1 docs ([[tasks]], [[metrics]], [[validity]]) updated in step with Turn 5; [[interface]] and [[extensions]] rewrites remain pending. Turn 6 candidates: (1) sign off on first-book asset choice (AI-written novella to spec, Claude's pick) and proceed to first-book drafting; (2) rewrite [[interface]] and affected parts of [[extensions]] to match the now-Agreed event-typed contract.
