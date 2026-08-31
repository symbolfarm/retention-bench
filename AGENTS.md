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

**retention-bench** is a research *instrument* — a workbench, not a benchmark. It adopts
[Continual Learning Bench](https://arxiv.org/abs/2606.05661)'s (Asawa et al., Apache-2.0)
runner, task interface and evaluation contract, and points them at a different question, using
a **hard RESET** (a process-kill discontinuity where only an on-disk survive-dir persists) and
a **mechanism-agnostic** SUT contract — fine-tuning, structural growth, notes and retrieval are
all modes above one process-level interface. Nothing constructive ships in this repo.

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
| How to publish | `RELEASING.md` |

## Conventions

**Branches.** One branch, `main`, with the full working history. Releases are annotated tags
plus GitHub Releases, cut from `main` — see `RELEASING.md`. There is no promotion step and no
public/private path split; both were retired with the orphan-`main` model in RB-22.

**What is public.** Everything is. The invariant is not "these paths are safe to show" but
**nothing in this repo is unpublishable** — `.tasks/`, `TASKS.md`, this file, `feedback/`,
`history/`, `notebook/`, `docs/archive/` and `docs/reviews/` are all part of what makes the
instrument inspectable. Write accordingly: no credentials, no third-party personal details, and
nothing you would not want read by the people it discusses.

**Tasks.** Use the `work-cycle` skill. A brief is a *handoff artifact*: write one when work is
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

*If the venv is broken after a container rebuild* — only `/workspace` is host-backed, so the
uv-managed interpreter and any checkout outside `/workspace` are container-local and do not
survive. Repair (2026-08-05):

```bash
uv python install 3.13                       # heals the dangling .venv/bin/python symlink
uv pip install --python .venv/bin/python -e /workspace/continual-learning-bench
```

The second line is the `cl-benchmark` pin, which **must** be editable — as a wheel it silently
drops the task data files and every task construction fails. Keep that checkout on the SHA in
`pyproject.toml`. It lives in `/workspace` deliberately, so the next rebuild does not take it.

**Commits.** Trailer: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Doc hygiene

`tests/test_docs_links.py` asserts that every relative link in the tracked markdown resolves. If
you move or delete a doc, that test tells you what you broke — which is the entire reason it
exists.

`tests/test_doc_claims.py` goes one step further: it asserts the prose is still *true*. Every
source anchor in `pages/map.js` must name a live Python symbol or markdown heading, and every
quoted ε / schedule-size number must match the code that defines it. Rename `observe`, retune
`EPSILON`, or reshape the default schedule and it names every file that now lies. Use symbol
and heading anchors, never line numbers — a line number is correct only on the day it is
written and has no way to stay correct.

Prefer facts that are **executable** (a test or a command fails when they drift) or **adjacent**
(a module docstring, so a code change drags them into the same diff) over prose in a separate
file. Prose in a separate file is what rots, and this file is the cautionary example.
