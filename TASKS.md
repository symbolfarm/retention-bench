# Tasks

> **Agents:** read this file at the start of every session, then consult
> `.tasks/LOG.jsonl` for the current task queue. The `task-cycle` skill
> (in `~/.claude/skills/task-cycle/SKILL.md`) describes how to start and complete
> tasks. Use `~/.claude/skills/task-cycle/assets/task-template.md` when creating
> new task files.

## Current focus

**⛔ Next session, start here: B4c is blocked on a Docker-capable environment.**
B4a (launch engine) and B4b (Dockerfiles) landed 2026-05-30, but **B4c cannot
proceed in this dev container** — no host `docker.sock`, unprivileged, and a
seccomp filter blocks user namespaces so even rootless Docker won't run. Before
resuming B4, **rebuild the dev container for DooD** (bind-mount host
`/var/run/docker.sock`, install `docker-ce-cli`, grant `agent` socket access,
set `HOST_WORKSPACE`). Full spec in the B4c backlog entry below + the
`AgentDesk dev env` memory. Until then there is **no unblocked task** in the
queue. *(Earlier MVP focus, below, is complete as of M7 — kept for context.)*

---

**Operational MVP for the book-track.** Goal: a runnable end-to-end smoke test
where the harness drives a no-state reference SUT through a toy book-track task,
produces a trace, scores it, and renders a retention curve. No cohort-1 assets,
no LLM-judge scoring, no container packaging — just the smallest thing that
exercises the full pipeline.

Definition of done for MVP: `./run.sh smoke-test` produces a JSONL trace and a
printed `P`/`C`/`R(k)` retention curve, end-to-end, on the no-state SUT.
**Status: ✓ met at M7 (2026-05-20).**

**Stack (decided 2026-05-20):** Python for harness + reference SUTs. Anthropic
SDK for the no-state SUT's LLM calls. Rust port of the harness is a possible
post-MVP learning exercise; the SUT contract is process-level so cross-language
ports are free once the contract is stable.

## MVP task list (proposed — not yet filed)

Tasks numbered M1–M7 are the candidate MVP build order. They will be filed as
individual `.tasks/M*.md` task files after a debrief pass.

1. **M1 — Trace schema spec.** Write `docs/trace-schema.md` defining the JSONL
   event stream format and per-`QUIZ` record schema. Resolves the structural
   details deferred from decision #1. Pure spec; no code.
2. **M2 — Harness skeleton (event loop + DIR lifecycle).** Read a task
   definition, run the `READ`/`QUIZ`/`RESET` loop, manage subprocess and `DIR`
   (incl. tar.gz + bytes-on-disk snapshotting per #8), emit trace. Stub SUT for
   testing.
3. **M3 — SUT interface spec + no-state reference SUT.** Small spec for the SUT
   binary contract (stdin/stdout vs. files). Implement the no-state baseline:
   call an LLM API with `STAGE_INPUT`, return response, ignore `DIR`.
4. **M4 — Wire harness + no-state SUT end-to-end.** First integration; harness
   actually drives a real SUT through a trivial task definition.
5. **M5 — Smoke-test task definition.** Short placeholder text (~1–2 pages) +
   ~5 questions, three probes per question. Explicitly labelled smoke-test, not
   cohort-1.
6. **M6 — Exact-match scorer + retention-curve renderer.** Pure function over
   the trace, emits `P`, `C`, `R(k)` per question and aggregate curve. Per
   decision #6, exact-match is enough for MVP; LLM-judge integration is
   post-MVP.
7. **M7 — End-to-end smoke run.** Execute M5 via M2 + M3, score with M6,
   produce curve. The "operational MVP" milestone.

## Backlog (post-MVP, not yet ordered)

- B1 — notes-LLM reference SUT (decision #11). ✓ **Done** (2026-05-25).
- B2 — naive-RAG reference SUT (decision #11). ✓ **Done** (2026-05-26; pluggable embedder seam, interim `sentence-transformers` default, llama-cpp wired).
- B3 — LLM-as-judge scorer (decision #6). ✓ **Done** (2026-05-26; **hand-rolled** judge behind a `Scorer` seam — *not* a library; see decisions-checklist #6).
- B4 — Docker container packaging + tier-declaration scaffolding (decision #16). **Split** (2026-05-30) into B4a/B4b/B4c — oversized for one session. See `.tasks/debriefs/B4.md`.
  - B4a — harness docker-run launch engine + manifest `image`/`env` contract. ✓ **Done** (2026-05-30; commit `16bf61b`).
  - B4b — four SUT Dockerfiles (shared slim API base + separate torch-CPU base for constructive) + README packaging notes. ✓ **Done** (2026-05-30; commit `51f6625`). Caveat: images are **build-UNVERIFIED** — no Docker daemon in this dev container.
  - **B4c — ⛔ BLOCKED ON ENVIRONMENT. Read this before next session.** Needs a **Docker-capable environment**, which this dev container is not: no host `docker.sock`, unprivileged (`CapEff: 0`), and a seccomp filter blocks `unshare(CLONE_NEWUSER)` so even *rootless* Docker can't run (diagnosed 2026-05-30). **Action before resuming B4c:** rebuild the dev container for DooD — bind-mount host `/var/run/docker.sock`, install `docker-ce-cli` (client only), give the `agent` user socket access, and set `HOST_WORKSPACE=<host path of /workspace>`. Full spec + rationale in the `AgentDesk dev env` memory and `.tasks/debriefs/B4b.md`. Scope: real `docker build` verification of all six images, add `image` field to the four manifests + a harness force-subprocess opt-out (so the always-on tests stay green), bare-host + dev-container smoke paths, QUICKSTART, tier-metadata audit flow. See refined brief `.tasks/B4c-smoke-and-tier-audit.md`.
- B5 — Mock tool-call transcript authorship strategy + first in-context-leaderboard variant (decision #7 deferred sub-decision).
- B6 — `docs/interface.md` rewrite to match Turn 3 five-thing contract + two-leaderboard resolution.
- B7 — `docs/metrics.md` write-in: resolved `C` definition (text-in-context + accumulated `QUIZ` history) + storage-delta-= 0 rule for in-place training + FLOPs reporting fields.
- B8 — Cohort-1 novella dispatch (blocked on Toby's sign-off; orthogonal to harness MVP).
- B9 — Provider-neutral LLM calls via the OpenAI-compatible API (OpenRouter). ✓ **Done** (2026-06-03; commits `6be9374` + `c460bc8`). **Rescoped** (2026-06-03, with Toby) from "general provider framework" to: point the three text SUTs + the judge at an OpenAI-compatible `base_url` via the `openai` SDK — SUTs default `deepseek/deepseek-v4-flash`, judge pinned `moonshotai/kimi-k2.6`. No shared package (client construction inlined per component, ~3 lines each). The `NAIVE_RAG_EMBEDDER` seam was **deliberately left out of scope** (local dense retrieval, not a provider LLM call) — a reversal of the 2026-05-26 scope-growth note above. Live-verified end-to-end against OpenRouter (deepseek SUT + kimi judge function-calling). Follow-ups filed: boundary token-counting proxy; open-model judge quality validation. See `.tasks/debriefs/B9.md`.
- B10 — Harness integration tests against a fake LLM client. The unit-test suite uses the stub SUT, so it doesn't exercise the real subprocess + SDK + token-accounting path. M7 surfaced two harness bugs (`_run_reset` PYTHONPATH-drop; SUT-reported resource fields dropped on the floor) that no test currently catches. A fake client (returns canned responses, reports synthetic token counts) driving the real SUTs through the real harness would catch this class of bug and protect the audit-trail fidelity that future published retention curves rely on. **Largely already delivered:** `tests/fake_openai_shim/` + `tests/test_*_fake_openai.py` (rebuilt from the old fake-anthropic shim in B9, 2026-06-03) drive all three real SUTs through the real harness and assert exactly those M7 resource-accounting regressions. Revisit only if B10 wants coverage beyond what now exists (e.g. fault-injection / error-path cases). Surfaced 2026-05-20 during M7 wrap-up.
- B11 — Wire judge token usage into a separate `judge_resource_appendix` (decision #6). B3 documented the architecture but `JudgeScorer.score()` currently drops `response.usage`. Surfaced 2026-05-26 during B3 wrap-up.
- B12 — Smoke-task gold-answer quality pass: q4 gold "a heartbeat" is too terse, so substance-correct answers fail exact-match and (being `surface_factual`) aren't rescued by the judge. Asset fix, not a scorer fix. Surfaced 2026-05-26 during B3 wrap-up.

## Structure

```
.tasks/
├── LOG.jsonl              # Append-only audit log of all tasks
├── debriefs/              # One debrief file per completed task
│   └── M1-....md
├── M2-....md              # Pending/active task files (deleted on completion)
└── M3-....md
```

## Quick reference

| What | Where |
|---|---|
| Full task queue | `.tasks/LOG.jsonl` |
| Active task files | `.tasks/*.md` |
| Completed debriefs | `.tasks/debriefs/` |
| Task template | `~/.claude/skills/task-cycle/assets/task-template.md` |
| Debrief template | `~/.claude/skills/task-cycle/assets/debrief-template.md` |
| Skill instructions | `~/.claude/skills/task-cycle/SKILL.md` |
