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

For the cross-project framing of how this eval composes with the sibling projects (constructive-neural-networks and eureka-tokens), see [research-stack-synthesis](https://github.com/symbolfarm/meta-research/blob/main/projects/research-stack-synthesis.md) — CL-eval supplies the **measurement** slot in the trigger-operator-measurement triple.

Two **areas of focus** for task and reference-mode design (not protocol bifurcations):

- **Agent-memory area** — externally-legible framing; most current memory-system work lives here, so most external interest will land here first.
- **Constructive area** — priority area for this project's owner; the constructive-neural-networks project depends on this evaluator existing.

Task and reference-mode design decisions resolve the way constructive-area concerns dictate, but the agent-memory area keeps its seat because (a) it's the more externally legible framing and (b) v0.1 of the spec already invested heavily in it.

## Entry points

- `AGENTS.md` — orientation for a fresh agent resuming the project. Read first.
- `TASKS.md` + `.tasks/` — current MVP task queue (task-cycle skill).
- `docs/decisions-checklist.md` — resolved design decisions. Load-bearing for what we're building.
- `docs/spec.md` — the v0.1 design spec, promoted from `scratch/`. **Read for the protocol shape, not as a final commitment to scope.**
- `history/design-dialogue.md` — joint-scoping conversation, all turns. Superseded by the decisions checklist; consult for "why" archaeology.
- `history/handover.md` — earlier read-order guide; predates Turn 5/6, superseded by `AGENTS.md`.

The other spec documents under `docs/` (`protocol.md`, `interface.md`, `metrics.md`, `tasks.md`, `topology.md`, `validity.md`, `extensions.md`, `open-questions.md`) are reference material — *v0.1 starting points*, not stable specifications. `docs/interface.md` in particular is slated for rewrite.

## What this project owes other projects

- **constructive-neural-networks** depends on the weight-update track existing in some form. CNN's branch-promotion gate ("read the eval before drilling into target signal or unit-of-construction") was set against this project's previous shape (a deferred extension); promoting + reopening scope satisfies the dependency-shape that CNN actually needs.

## Communication norms

This project uses the **echo-back / design-dialogue / idea-tree** joint-scoping pattern, same as the CNN project. See `feedback/joint-design-dialogue-pattern.md` and `feedback/echo-back-communication-norms.md`. The CNN project is pilot #1 of this mode; this is pilot #2.

## Status

**MVP implementation cleared (2026-05-20).** All 16 active decisions in `docs/decisions-checklist.md` resolved; #17 (train/no-train lane) deferred. Headline resolutions: atomic-event model (`READ`/`QUIZ`/`RESET`) with three-probe baselines (`P`/`C`/`R(k)`) and `(R−P)/(C−P)` normalised retention; thin test harness + SUT-internal scaffolding; two leaderboards (agentic vs. in-context with mock tool-call transcripts); constructive-SUT weights accounted as a delta in `DIR` (in-place training → storage delta = 0, FLOPs becomes the load-bearing cost signal); five hardware tiers (Consumer / 1×H100 / 8×H100 / API / Open).

Build order tracked in `TASKS.md` + `.tasks/LOG.jsonl` under the `task-cycle` skill.
