---
title: AGENTS.md — orientation for fresh agents working on retention-bench
project: retention-bench
tags: [orientation, conventions]
---

# AGENTS.md

Orientation for an agent picking this project up.

**This file holds only things that do not change when the code changes.** Project status, the
current queue, the doc index, and research direction all live elsewhere and are maintained
there — see "Where to look". Do not restate them here: doing so is how this file went two
pivots stale, describing a book-track benchmark that had been deleted and a read order of
thirteen archived or non-existent documents.

## What this repo is

**retention-bench** is a research *instrument* — a workbench, not a benchmark. It extends
[Continual Learning Bench](https://arxiv.org/abs/2606.05661) (Asawa et al., Apache-2.0) with
two things CL-Bench lacks: a **hard RESET** (a process-kill discontinuity where only an on-disk
survive-dir persists) and a **constructive/parametric system class**.

There is no leaderboard and no submission process. The claim under test: *continual learning
agents need expanding memory — episodic memory growing across sessions, semantic memory growing
across episodes.* In-context learning abstracts richly but persists nothing; retrieval persists
a recording and re-derives the abstraction each session, over a retrieved subset. Neither keeps
the abstraction. See `README.md` and `docs/ROADMAP.md`.

## Where to look

| For | Read |
|---|---|
| Current status, focus, open queue | `TASKS.md`, then `.tasks/LOG.jsonl` |
| Repo tour — what every directory and doc is | `docs/README.md` |
| Research direction, probe ladder, open questions | `docs/ROADMAP.md` |
| Public framing and the measured reference ladder | `README.md`, `docs/reference-ladder.md` |
| Metric definitions | `docs/metrics.md` |
| How to publish | `RELEASING.md`, `PUBLIC_PATHS` |

## Conventions

**Branches.** `dev` is the working branch — everything lands here, including every edit to
public files. `main` is an **orphan** public snapshot with no shared history, produced only by
`scripts/promote.sh`. **Never hand-edit `main`**; the next snapshot would overwrite it. See
`RELEASING.md`.

**What is public.** `PUBLIC_PATHS` is the single source of truth for what reaches `main`.
Anything unlisted is dev-only — `.tasks/`, `TASKS.md`, this file, `feedback/`, `history/`,
`scratch/`, `scripts/`, `docs/archive/`, `docs/reviews/`.

**Tasks.** Use the `task-cycle` skill. A brief is a *handoff artifact*: write one when work is
going to a subagent or a future session, or when it is gated on review. Work you do yourself in
one sitting is a `chore:` or `docs:` commit, with a short "Decisions" paragraph in the message
body if you made a judgment call worth recording.

**One task, one repo.** `constructive-retention` is a sibling repo (checked out beside this one),
not co-edited from here. It is the constructive SUT this instrument exists to measure, and it
speaks the process-level contract in `docs/sut-interface.md`. Work needed there is a separate
task filed there (prefix `CR-`) that lands first; record the dependency with a
`Depends-on (external):` line.

**Python.** The dev loop uses `.venv/bin/python` (3.13); `./run.sh` prefers it automatically.
Override with `RETENTION_BENCH_PYTHON=/path/to/python`.

**Commits.** Trailer: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Doc hygiene

`tests/test_docs_links.py` asserts that every relative link in the tracked markdown resolves. If
you move or delete a doc, that test tells you what you broke — which is the entire reason it
exists.

Prefer facts that are **executable** (a test or a command fails when they drift) or **adjacent**
(a module docstring, so a code change drags them into the same diff) over prose in a separate
file. Prose in a separate file is what rots, and this file is the cautionary example.
