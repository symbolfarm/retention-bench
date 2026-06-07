# C7 Upstream PRs — plugin entry-point discovery (+ optional reset schedule)

**Priority:** low
**Blocked by:** nothing
**Touches:** `unknown` (CL-Bench fork/PR, not this repo)

## Context

CL-Bench's registry discovers systems/tasks by internal filesystem scan only —
no entry-point/plugin hook — so an external package registers via a thin launcher
that imports-then-delegates (the C0/C2 approach works fine this way). A small
upstream PR adding entry-point discovery would let `retention_bench` register
cleanly. Optional second PR: a first-class per-boundary reset schedule (we do this
system-side today, so it's a convenience, not a need).

Good-citizen PRs that also seed the relationship (coordinate with C5).

## Goal

One or two upstream PRs against `pgasawa/continual-learning-bench`.

## Acceptance criteria

- [ ] PR 1: entry-point plugin discovery in `registry.py`, backward compatible.
- [ ] (optional) PR 2: first-class reset schedule in the runner.
- [ ] Coordinated with the authors (C5) before opening.

## Decisions already made

- Neither PR is a blocker for our work (C0 finding); these are upstreaming, not
  prerequisites.

## Out of scope

Our own package changes (C2).
