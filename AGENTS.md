---
title: AGENTS.md — orientation for fresh agents resuming retention-bench
project: retention-bench (continual-learning-eval)
last_updated: 2026-05-17
tags: [orientation, handover]
---

# AGENTS.md

Orientation for a fresh agent (Claude or otherwise) picking this project up. Read this first.

## What this repo is

**retention-bench** (working name; aka CL-N, continual-learning-eval): a research project designing a benchmark that measures how gracefully an LLM-agent system's task performance degrades across discontinuities that erase working state. Headline artifact is a *retention curve* over `k` resets, normalised by per-question prior/ceiling probes.

Own GitHub repo: `symbolfarm/retention-bench` (split from `knowledge-graph-spec` on 2026-05-17, commit `0a43451`). Not under `meta-research/projects/`.

## Status

**Phase: scoping, late-stage.** Joint-scoping mode (pilot #2 of the design-dialogue pattern). Through Turn 6 of the design-dialogue. Eval philosophy is locked (cross-reset purity + three-probe baselines `P`/`C`/`R(k)` + normalised retention `(R−P)/(C−P)`). The agnostic five-thing interface has survived a book-track pressure-test.

**Close to first eval task.** What's gating implementation is in `decisions-checklist.md` — a set of design decisions with options drafted and recommendations made, awaiting Toby's sign-off.

## Communication norms — read before responding

Joint-scoping / echo-back mode. **Do not start implementing on first contact.** Default action when picking up the project is to read, echo back understanding, and surface trade-offs.

- `feedback/joint-design-dialogue-pattern.md`
- `feedback/echo-back-communication-norms.md`
- Auto-memory: `feedback_joint_scoping_norms.md` (should auto-load)

## Read order

1. **This file.**
2. `README.md` — project overview, eval philosophy, status.
3. `decisions-checklist.md` — current open decisions blocking first implementation.
4. `handover.md` — post-Turn-4 handover (still mostly current; predates Turn 5/6).
5. `tasks.md` — Track 1 (book-episodic) under the atomic-event model.
6. `metrics.md` — three-probe normalisation, retention curve, resource metrics.
7. `book-spec.md`, `memory-targets-spec.md`, `cohort-1-seeds.md` — the cohort-1 novella pipeline (specs ready, not yet dispatched).
8. `validity.md`, `protocol.md`, `interface.md` — reference material; `interface.md` is v0.1 and slated for rewrite to match the Turn 3 five-thing contract.
9. `design-dialogue.md` — full scoping dialogue, all turns. Long; consult on demand.
10. `open-questions.md`, `extensions.md`, `topology.md`, `worked-example-book-track.md`, `question-set-spec.md` — read on demand.

## Architectural direction (confirmed 2026-05-17)

- **Custom harness** for the protocol: `READ` / `QUIZ` / `RESET` event loop, process kill, `DIR` lifecycle, probe bookkeeping. No existing framework fits this.
- **Existing scorer library** (DeepEval `GEval` / Inspect AI scorers / `lm-eval` metrics) for per-`QUIZ` scoring. Harness emits a standardised per-question records file; scoring is a pure function over it, library-swappable.

## What is *not* yet decided

See `decisions-checklist.md`. Highlights:

- Verbatim-caching default (strict vs. permissive) — load-bearing for what the headline curve means.
- Question-author confound strategy (rotate vs. hold constant + audit).
- Trace/record format schema details.
- `C` operational definition needs to be written into `metrics.md` explicitly (Toby clarified 2026-05-17: text-in-context + accumulated `QUIZ` history).
- Reference SUT specs (no-state, notes-LLM, naive-RAG).

## What *not* to do without asking

- **Do not start writing harness or SUT code** until the checklist items marked hard-blocker are resolved.
- **Do not move or restructure the top-level docs.** Toby has flagged that the doc set will be reorganised into subdirectories soon to reduce clutter — but the reorganisation itself is a decision to make jointly, not unilaterally.
- **Do not dispatch the cohort-1 novella briefs** to author models. The seeds are drafted (`cohort-1-seeds.md`) but await Toby's sign-off on seed assignments and choice of question-author model.
- **Do not treat the v0.1 doc set as stable spec.** It's Toby's own draft, actively renegotiable. `interface.md` in particular is superseded by the Turn 3 agnostic five-thing contract and slated for rewrite.

## Sibling-project context

- **constructive-neural-networks** (in `symbolfarm/meta-research/projects/constructive-neural-networks/`) depends on this evaluator existing. CNN's target is constructive *transformers* (growth in attention/embeddings/MLPs of a pre-trained reasoning LM) — see auto-memory `project_constructive_transformers.md`.
- The cross-project framing (this eval as the *measurement* slot in a trigger-operator-measurement triple) lives in `symbolfarm/meta-research/projects/research-stack-synthesis.md`.

## Session log (recent)

- **2026-05-17.** Review pass by Claude over the v0.1 doc set after Turn 6. Outputs: `decisions-checklist.md` (this checklist), `AGENTS.md` (this file). Direction confirmed: custom harness + existing scorer library. `C` definition clarified by Toby (text-in-context + prior-`QUIZ`-history). No code yet.
