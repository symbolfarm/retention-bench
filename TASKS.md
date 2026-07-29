# Tasks

> **Agents:** read this file at the start of every session, then consult
> `.tasks/LOG.jsonl` for the current task queue. The `task-cycle` skill describes
> how to start and complete tasks; use its task template when creating new task
> files.

## Current focus

**PIVOT (2026-06-07): retention-bench is now an extension on top of Continual
Learning Bench** (Asawa et al., arXiv 2606.05661, Apache-2.0), not a standalone
benchmark. We adopt their harness / task-ABC / metrics / leaderboard and
contribute the two things they explicitly lack: a **hard RESET** (process-kill
discontinuity where only an on-disk survive-dir persists) and a
**constructive/parametric system class**. Full rationale + reuse/retire map:
[`docs/archive/clbench-pivot-plan.md`](docs/archive/clbench-pivot-plan.md)
(archived dev-only by C18). See also [[project_clbench_pivot]].

The C0-C4 pivot path is complete: the CL-Bench adapter seam works, the production
`SubprocessSystem` owns hard process-kill resets and reset schedules, the
constructive reference SUT runs through CL-Bench, and `gain_curve` renders the
reset-axis retention table with CL-Bench mean-gain reconciliation. The first
small curriculum substrate has also landed: `symbolic_associative_retention` is
a deterministic, exact-scored Retention Bench task with a keyless JSON-state
reference SUT (`suts/associative_memory`) that demonstrates a non-excluded
hard-reset retention band.

**REFRAME (2026-07-29): research instrument, not a benchmark.** Pre-release discussion
re-confirmed the June pivot's intent, which had been quietly drifting: retention-bench is
the *instrument* a research programme uses and shares publicly, not a standalone benchmark
seeking submissions. One owned task, co-designed with constructive-retention, no external
users, unsettled cost metric — that is an instrument, and it is the correct stage. Adoption
follows an interesting result, not benchmark infrastructure. The name stays (`bench` reads
as *workbench*); the docs must say so. Thesis: **storage is not memory** — in-context
learning and retrieval produce *access* without *integration*. RESET's justification:
it **converts a one-time cost into a recurring one**, which is what makes the scaling
difference visible. Filed as RB-16/17/18/19 below.

**Current open queue (see `.tasks/LOG.jsonl` as source of truth):**

- ~~**RB-16**~~ — **done 2026-07-29.** Widened the attribute/bin sets to 16 (chance
  0.5 → 0.0625), added a never-bridged held-out composition split mirroring
  constructive-retention, added the `random_guess` chance rung, and re-measured the
  ladder at the new 112-instance default. Two reference SUTs were retuned to the new
  schedule (`bounded_memory` cap 8→40, `reset_lossy` rate 0.05→0.01). See the debrief.
- ~~**RB-17**~~ — **done 2026-07-29.** README reframed as a research instrument: thesis
  up front, "bench" glossed as *workbench*, the RESET justified as converting a one-time
  cost into a recurring one, an honest scope-limits section (one owned task, co-design
  hazard named, no LLM measured yet), all figures re-checked against the post-RB-16
  ladder, and `docs/ROADMAP.md` linked as the agenda. See the debrief.
- ~~**RB-18**~~ — superseded 2026-07-29: not task-sized, written directly as
  [`docs/ROADMAP.md`](docs/ROADMAP.md). Functions as **pre-registration** — the probe design
  and thesis are on record before constructive-retention is measured through the instrument.
- **RB-19** *(high, blocked by RB-16)* — first real LLM measurement, agentic
  (iterative-retrieval) SUT. The instrument has never measured an LLM; the headline claim is
  currently unfalsified in either direction.
- **RB-3** — paused repeated-exposure curriculum variant for sample-efficiency /
  RL-adjacent exploration; resume after constructive-retention SUTs have advanced
  enough to make exposure-count curves informative.
- **C5** — author outreach draft, gated on Toby review before anything is sent.
- **C6** — superseded by **RB-2** after the curriculum-learning strategy pivot.
- **C7** — optional upstream PRs / plugin-hook work.
- **C12** — non-root SUT containers.
- **C17** — cut the orphan public `main` release branch; stop before pushing.
  **Land RB-14 (doc pass) first** so the first public snapshot is already clean.

**From the 2026-07-07 v0.1 review** (`docs/reviews/2026-07-07-v0.1-review.md`).
RB-10 (RESET process-group integrity), RB-11 (scorer packaging + CI), RB-13
(robustness batch, incl. the book-track dead-code sweep) landed 2026-07-17, and
RB-12 (bootstrap CIs + post-reset-window `W(m)`/`W_norm` + ε relative to
`r_max`) and RB-14 (public doc pass: codename sweep, dangling refs, metric
status tags, editable-install documentation, `!docs/reviews/` exclude, repo
tour in `docs/README.md`) landed 2026-07-19 — see their debriefs. **The
2026-07-07 review queue is now clear.**

**C17 (public `main` cutover) is staged but NOT pushed.** The local `main` orphan snapshot
is from 2026-06-24 and is now ~78 files / +4.6k lines behind `dev` on public paths (RB-12,
RB-13, RB-14 and the new tests are all missing from it). **Do not push that commit.** The
sequence is: land RB-16→RB-19 → `scripts/promote.sh release` for a fresh snapshot → then
Toby pushes host-side (SSH is host-only in the dev container) and flips visibility.

**Cross-repo keystone:**

- **RB-15** *(high, **UNBLOCKED 2026-07-20** — constructive-retention CR-22 landed)* — claim
  **Milestone 2**: wire the constructed-hop-2 SUT into a `--mode` and take the gain-vs-`k`
  curve (RB-12's bootstrap CIs + `W_norm` are now available for it). CR-22's constructed
  hop-2 runs at ceiling (held-out composed 1.000±0.000, additive + online, RESET-survived,
  n=10 — see CR debrief `CR-22-two-stage-chaining.md`), so a real additive-by-construction
  increment now exists; it should give the first non-degenerate band (retention flat in
  `k`). Will spawn a small CR-side `--mode` companion task when picked up.

The repo-local dev loop uses `.venv/bin/python` (Python 3.13). CL-Bench is
installed into that venv from the pinned dependency, with the editable source
checkout at `/home/agent/src/cl-bench` when local debugging is needed. `./run.sh`
prefers `.venv/bin/python` automatically; override with
`RETENTION_BENCH_PYTHON=/path/to/python` if needed.

**Dropped by the pivot / later queue cleanup:** B4c (docker/tier — CL-Bench owns
packaging), B14 (judge quality — no judge anymore), B16 (token proxy — CL-Bench
owns cost accounting), C8 (agentic multi-step adapter deferred behind the
curriculum/constructive-SUT path). Marked `superseded` in the log; see their
debriefs.

---

## Historical: standalone-benchmark era (M1–M7, B1–B16) — SUPERSEDED, then RETIRED

**Retired by C20 (2026-06-11).** The book-track path is gone, not just
superseded: the event-loop harness (`harness/event_loop.py`, `task_loader.py`,
`trace_writer.py`, `__main__.py`), the per-question scorer (`scorer/`'s
exact-match/judge/curve/CLI — only `EPSILON` + `normalised_retention` survive in
`scorer/aggregate.py`), the `tasks/smoke-test/` fixture, the `no_state` +
`naive_rag` reference SUTs, and their tests were deleted. `./run.sh smoke` now
runs the keyless `bsm_accumulator` SUT through `retention_bench.gain_curve` on
CL-Bench's `blind_spectrum_monitoring`, offline and keyless. What the pivot
**reused** stays: `harness/sut_process.py`, `harness/dir_lifecycle.py`,
`scorer.aggregate`'s band primitives, and `suts/constructive/`. The book-track
input/output schema docs were re-archived to `docs/archive/` (dev-only).

The MVP build order (M1–M7) and backlog (B1–B16) below are kept for "why"
archaeology only. For reference, the book-track MVP's definition of done was a
`./run.sh smoke-test` that drove a no-state SUT end-to-end to a `P`/`C`/`R(k)`
curve (✓ met at M7, 2026-05-20); that pipeline no longer exists.

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
- B4 — Docker container packaging + tier-declaration scaffolding (decision #16). **Split** (2026-05-30) into B4a/B4b/B4c — oversized for one session. See `.tasks/debriefs/B4-docker-packaging-and-tiers.md`.
  - B4a — harness docker-run launch engine + manifest `image`/`env` contract. ✓ **Done** (2026-05-30; commit `16bf61b`).
  - B4b — four SUT Dockerfiles (shared slim API base + separate torch-CPU base for constructive) + README packaging notes. ✓ **Done** (2026-05-30; commit `51f6625`). Caveat: images are **build-UNVERIFIED** — no Docker daemon in this dev container.
  - **B4c — ⛔ BLOCKED ON ENVIRONMENT. Read this before next session.** Needs a **Docker-capable environment**, which this dev container is not: no host `docker.sock`, unprivileged (`CapEff: 0`), and a seccomp filter blocks `unshare(CLONE_NEWUSER)` so even *rootless* Docker can't run (diagnosed 2026-05-30). **Action before resuming B4c:** rebuild the dev container for DooD — bind-mount host `/var/run/docker.sock`, install `docker-ce-cli` (client only), give the `agent` user socket access, and set `HOST_WORKSPACE=<host path of /workspace>`. Full spec + rationale in the `AgentDesk dev env` memory and `.tasks/debriefs/B4b-sut-dockerfiles.md`. Scope: real `docker build` verification of all six images, add `image` field to the four manifests + a harness force-subprocess opt-out (so the always-on tests stay green), bare-host + dev-container smoke paths, QUICKSTART, tier-metadata audit flow. See refined brief `.tasks/B4c-smoke-and-tier-audit.md`.
- B5 — Mock tool-call transcript authorship strategy + first in-context-leaderboard variant (decision #7 deferred sub-decision).
- B6 — `docs/interface.md` rewrite to match Turn 3 five-thing contract + two-leaderboard resolution.
- B7 — `docs/metrics.md` write-in: resolved `C` definition (text-in-context + accumulated `QUIZ` history) + storage-delta-= 0 rule for in-place training + FLOPs reporting fields.
- B8 — Cohort-1 novella dispatch (blocked on Toby's sign-off; orthogonal to harness MVP).
- B9 — Provider-neutral LLM calls via the OpenAI-compatible API (OpenRouter). ✓ **Done** (2026-06-03; commits `6be9374` + `c460bc8`). **Rescoped** (2026-06-03, with Toby) from "general provider framework" to: point the three text SUTs + the judge at an OpenAI-compatible `base_url` via the `openai` SDK — SUTs default `deepseek/deepseek-v4-flash`, judge pinned `moonshotai/kimi-k2.6`. No shared package (client construction inlined per component, ~3 lines each). The `NAIVE_RAG_EMBEDDER` seam was **deliberately left out of scope** (local dense retrieval, not a provider LLM call) — a reversal of the 2026-05-26 scope-growth note above. Live-verified end-to-end against OpenRouter (deepseek SUT + kimi judge function-calling). Follow-ups filed: **B16** (boundary token-counting proxy), **B14** (open-model judge quality validation), **B15** (benchmark validity watch-items). See `.tasks/debriefs/B9-openai-compat-client.md`.
- B10 — Harness integration tests against a fake LLM client. ✓ **Done** (2026-05-20; commit `07b741c`). The unit-test suite uses the stub SUT, so it doesn't exercise the real subprocess + SDK + token-accounting path. M7 surfaced two harness bugs (`_run_reset` PYTHONPATH-drop; SUT-reported resource fields dropped on the floor) that no test currently catches. A fake client (returns canned responses, reports synthetic token counts) driving the real SUTs through the real harness would catch this class of bug and protect the audit-trail fidelity that future published retention curves rely on. **Largely already delivered:** `tests/fake_openai_shim/` + `tests/test_*_fake_openai.py` (rebuilt from the old fake-anthropic shim in B9, 2026-06-03) drive all three real SUTs through the real harness and assert exactly those M7 resource-accounting regressions. Revisit only if B10 wants coverage beyond what now exists (e.g. fault-injection / error-path cases). Surfaced 2026-05-20 during M7 wrap-up.
- B11 — Wire judge token usage into a separate `judge_resource_appendix` (decision #6). ✓ **Done** (2026-05-27; commit `fe0ca39`; appendix code later carried through the B9 OpenAI port). B3 documented the architecture but `JudgeScorer.score()` was dropping `response.usage`; now `JudgeScorer` accumulates per-call usage and the CLI writes `judge_resource_appendix.jsonl`. Surfaced 2026-05-26 during B3 wrap-up.
- B12 — Smoke-task gold-answer quality pass: q4 gold "a heartbeat" is too terse, so substance-correct answers fail exact-match and (being `surface_factual`) aren't rescued by the judge. Asset fix, not a scorer fix. ✓ **Done** (2026-05-27; commit `a868ecc`). Surfaced 2026-05-26 during B3 wrap-up.
- B13 — Constructive (train-and-grow) reference SUT (decision #11; the constructive-transformers tier). ✓ **Done** (2026-05-27; commit `85fedb6`). Torch-CPU SUT that grows capacity across `READ`/`RESET` and reports `kind:"local"` resource accounting.
- B14 — Open-model judge quality validation. The pinned judge (`moonshotai/kimi-k2.6`, set in B9) drives every retention score but its agreement with a stronger reference judge / human labels is unvalidated. Measure agreement (accuracy / κ) on the judge-eligible types, document in `docs/metrics.md`, recommend a pinned judge. Surfaced 2026-06-03 during B9 wrap-up.
- B15 — Benchmark validity watch-items (prior-saturation + question-type separation). ✓ **Done** (2026-06-03; commit `46d6872`). Per-`question_type` retention curve breakdown in `scorer/aggregate.py` (`aggregate_curve_by_type`) + render block, and the prior-saturation/material-novelty validity narrative + interpretation rule in `docs/metrics.md`. (1) The `C≈P` exclusion makes effective `n` model-dependent — as base models improve, priors saturate and questions fall out (B9 smoke: 4/5 excluded), making renewable *novel* synth material load-bearing for validity, not just variety (informs B5/B8). (2) Report retention curves broken down by `question_type` so notes_llm's `surface_factual`-vs-`multi_hop` separation is legible — the stenography-vs-understanding-transfer signal. Surfaced 2026-06-03 in discussion.
- B16 — Boundary token-counting proxy. Today the harness trusts SUT self-reported token usage; for a public-credibility artifact that's a reviewer's first attack. B9's `RETENTION_BENCH_BASE_URL` seam lets the harness interpose a forwarding proxy that tallies `usage` at the wire and reconciles against self-report (keeps the upstream key harness-side too). Surfaced 2026-06-03 during B9 wrap-up. *(NB: distinct from the completed `B13` constructive-SUT task — numbered B16 to avoid the ID clash.)*

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
