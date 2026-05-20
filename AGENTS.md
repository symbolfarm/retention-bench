---
title: AGENTS.md — orientation for fresh agents resuming retention-bench
project: retention-bench (continual-learning-eval)
last_updated: 2026-05-20
tags: [orientation, handover]
---

# AGENTS.md

Orientation for a fresh agent (Claude or otherwise) picking this project up. Read this first.

## What this repo is

**retention-bench** (working name; aka CL-N, continual-learning-eval): a research project designing a benchmark that measures how gracefully an LLM-agent system's task performance degrades across discontinuities that erase working state. Headline artifact is a *retention curve* over `k` resets, normalised by per-question prior/ceiling probes.

Own GitHub repo: `symbolfarm/retention-bench` (split from `knowledge-graph-spec` on 2026-05-17, commit `0a43451`). Not under `meta-research/projects/`.

## Status

**Phase: scoping, late-stage.** Joint-scoping mode (pilot #2 of the design-dialogue pattern). Through Turn 6 of the design-dialogue. Eval philosophy is locked (cross-reset purity + three-probe baselines `P`/`C`/`R(k)` + normalised retention `(R−P)/(C−P)`). The agnostic five-thing interface has survived a book-track pressure-test.

**Cleared for MVP implementation (2026-05-20).** All 16 active decisions in `docs/decisions-checklist.md` resolved; #17 (train/no-train lane) deferred. Task queue lives in `TASKS.md` + `.tasks/` under the `task-cycle` skill.

## Communication norms — read before responding

Joint-scoping / echo-back mode. **Do not start implementing on first contact.** Default action when picking up the project is to read, echo back understanding, and surface trade-offs.

- `feedback/joint-design-dialogue-pattern.md`
- `feedback/echo-back-communication-norms.md`
- Auto-memory: `feedback_joint_scoping_norms.md` (should auto-load)

## Repo layout (post 2026-05-20 housekeeping)

```
root/      README.md, AGENTS.md, TASKS.md, .tasks/
docs/      live specs + decisions (ongoing relevance)
history/   superseded artifacts kept for audit (design-dialogue, handover)
feedback/  joint-scoping mode docs
```

## Read order

1. **This file.**
2. `README.md` — project overview, eval philosophy, status.
3. `TASKS.md` + `.tasks/LOG.jsonl` — current MVP task queue (task-cycle skill).
4. `docs/decisions-checklist.md` — resolved design decisions; load-bearing for what we're building and why.
5. `docs/tasks.md` — Track 1 (book-episodic) under the atomic-event model.
6. `docs/metrics.md` — three-probe normalisation, retention curve, resource metrics.
7. `docs/book-spec.md`, `docs/memory-targets-spec.md`, `docs/cohort-1-seeds.md` — the cohort-1 novella pipeline (specs ready, not yet dispatched).
8. `docs/validity.md`, `docs/protocol.md`, `docs/interface.md` — reference material; `interface.md` is v0.1 and slated for rewrite to match the Turn 3 five-thing contract.
9. `docs/open-questions.md`, `docs/extensions.md`, `docs/topology.md`, `docs/worked-example-book-track.md`, `docs/question-set-spec.md` — read on demand.
10. `history/design-dialogue.md` — full scoping dialogue, all turns. Superseded by `docs/decisions-checklist.md`; consult only for "why" archaeology.
11. `history/handover.md` — post-Turn-4 handover. Predates Turn 5/6; superseded by this file + the decisions checklist.

## Architectural direction (confirmed 2026-05-17)

- **Custom harness** for the protocol: `READ` / `QUIZ` / `RESET` event loop, process kill, `DIR` lifecycle, probe bookkeeping. No existing framework fits this.
- **Existing scorer library** (DeepEval `GEval` / Inspect AI scorers / `lm-eval` metrics) for per-`QUIZ` scoring. Harness emits a standardised per-question records file; scoring is a pure function over it, library-swappable.

## What is *not* yet decided

All hard-blockers + soft-blockers resolved 2026-05-20. See `docs/decisions-checklist.md`. Outstanding spec follow-ups (now task-tracked, not decision-blocked):

- `docs/metrics.md` needs the resolved `C` definition (text-in-context + accumulated `QUIZ` history) written in explicitly.
- `docs/interface.md` v0.1 needs rewrite to match Turn 3 five-thing contract + the two-leaderboards (agentic / in-context with mock transcripts) resolution.
- Reference SUT specs (no-state, notes-LLM, naive-RAG) not yet drafted.
- Mock tool-call transcript authorship strategy for the in-context leaderboard (deferred from #7 resolution).

## What *not* to do without asking

- **Do not dispatch the cohort-1 novella briefs** to author models. The seeds are drafted (`docs/cohort-1-seeds.md`) but await Toby's sign-off on seed assignments and choice of question-author model.
- **Do not treat the v0.1 doc set as stable spec.** It's Toby's own draft, actively renegotiable. `docs/interface.md` in particular is superseded by the Turn 3 agnostic five-thing contract and slated for rewrite.
- **Do not delete `history/` files** without explicit user sign-off, even though they're tagged "superseded." They remain the audit trail for how the design got here.

## Sibling-project context

- **constructive-neural-networks** (in `symbolfarm/meta-research/projects/constructive-neural-networks/`) depends on this evaluator existing. CNN's target is constructive *transformers* (growth in attention/embeddings/MLPs of a pre-trained reasoning LM) — see auto-memory `project_constructive_transformers.md`.
- The cross-project framing (this eval as the *measurement* slot in a trigger-operator-measurement triple) lives in `symbolfarm/meta-research/projects/research-stack-synthesis.md`.

## Session log (recent)

- **2026-05-17.** Review pass by Claude over the v0.1 doc set after Turn 6. Outputs: `docs/decisions-checklist.md`, this file. Direction confirmed: custom harness + existing scorer library. `C` definition clarified by Toby (text-in-context + prior-`QUIZ`-history). No code yet.
- **2026-05-20.** All open decisions resolved (#7 two-leaderboard, #9 tool-call counting, new #14/#15/#16 covering constructive-SUT weights, FLOPs reporting, and five hardware tiers). Repo reorganised into `docs/` + `history/`. `TASKS.md` + `task-cycle` skill adopted. Cleared for MVP harness implementation.
