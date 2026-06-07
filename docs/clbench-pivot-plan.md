# CL-Bench Pivot Plan (draft)

**Status:** draft for joint-scoping — not yet locked.
**Date:** 2026-06-07.
**Supersedes:** the standalone-benchmark framing in `README.md` / `TASKS.md` (the M1–M7 MVP and most of B1–B16).
**Memory:** [[project_clbench_pivot]].

## 1. What changed

Continual Learning Bench (Asawa et al., arXiv 2606.05661; `github.com/pgasawa/continual-learning-bench`; Apache-2.0) published 2026-06-04 and substantially subsumes our agent-memory framing — 6 expert-validated domains, frontier leaderboard, funding, community. We stop competing on that ground and instead **build on CL-Bench as a library**, contributing the two things it explicitly lacks:

- **Hard RESET** — a process-kill discontinuity where only an on-disk state dir survives (their `reset_between_instances` is in-RAM only). New reporting axis: retention as a function of the number of hard resets `k`.
- **Constructive / parametric system class** — weight-update adaptation, which CL-Bench states in its Limitations it does not evaluate and invites as a community contribution. This is our priority ([[project_constructive_transformers]]; the CNN dependency).

## 2. Architecture direction  ⟵ load-bearing DECISION

**Proposed (recommend):** *adopt CL-Bench's harness, retire ours.* CL-Bench owns the runner, task ABC, per-instance reward + gain metric, and the leaderboard. We keep only what's non-duplicated and repackage it as contributions.

Rejected alternative: keep our `harness/` + `scorer/` and pull CL-Bench *tasks* in as data. This keeps our code but loses their leaderboard/credibility and leaves us maintaining a parallel harness — exactly the distraction we're trying to shed.

### Reuse / retire / verify

| Ours | Disposition |
|---|---|
| `harness/sut_process.py` (spawn, SIGKILL-on-RESET, JSONL channel, DIR cwd) | **REUSE** → becomes the guts of `SubprocessSystem(ContinualLearningSystem)` (Contribution A) |
| `harness/dir_lifecycle.py` (survive-dir, tar.gz snapshot, byte accounting) | **REUSE** → state-dir persistence + storage-delta signal |
| `suts/constructive/` (torch-CPU, grow across READ/RESET, checkpoint) | **REUSE** → headline parametric system (Contribution B) |
| `scorer/aggregate.py` reset-axis / per-type curve logic | **REUSE** → the net-new reporting layer over their rewards |
| FLOPs / storage-delta accounting ideas | **REUSE** → map to their `UsageEvent` / `record_usage_event` |
| `harness/event_loop.py` (the runner) | **RETIRE** → their `runtime/runner.py` |
| `harness/task_loader.py`, `tasks/smoke-test` format | **RETIRE** → their task ABC + 6 tasks |
| `scorer/judge.py`, `exact_match.py`, `curve.py` | **RETIRE** → their per-task reward + gain |
| `suts/notes_llm`, `suts/naive_rag`, `suts/no_state` | **DEPRIORITIZE** → duplicate their ICL-Notepad / Mem0 / stateless; keep only as adapter-parity sanity checks |
| B4* docker/tier scaffolding, two-leaderboard design | **DROP** → CL-Bench owns packaging + leaderboard |
| cross-reset purity rule; prior-saturation validity (B15) | **CARRY FORWARD** as task-design criteria, not code |

Honest cost: this supersedes most of the M1–M7 + B1–B16 build. The load-bearing *ideas* survive as contributions and task-design criteria; much of the *code* does not.

## 3. The real technical risk: instance granularity

Our SUT contract is **one event → one reply** (`READ`→`stage_output`, `QUIZ`→`answers`; `sut_process.send_event` is a single round-trip). CL-Bench's *instance* is **multi-step**: `system.respond(query)` is called repeatedly within one instance, with `observe(observation)` feedback between steps, until `task.step(...)` returns `done` (e.g. several SQL queries per DB-exploration question).

Implications:
- The JSONL channel already supports N round-trips against one handle — multi-step is an **adapter/loop change, not a contract change**.
- But our existing SUTs *answer once*; they're not agentic loops. The **constructive SUT doesn't need to be** — read → train → answer fits single-shot-style instances well.
- So: triage CL-Bench's 6 tasks for (a) cross-reset purity and (b) single-shot-vs-agentic shape. Target a **single-shot, retention-discriminative** task first; defer multi-step-agentic tasks (poker, DB exploration) until/unless we extend the SUT contract to in-instance turns.

## 4. Hard-RESET feasibility (good news: no fork needed to start)

Their runner calls `system.respond(query)` and optionally `system.reset()` between instances. A `SubprocessSystem` can hold its child process across `respond()` and, on `reset()`, **SIGKILL + respawn from state_dir** — i.e. a hard reset expressed entirely inside a system, using their existing `reset_between_instances=True` hook. **No core change required** for the basic reset; the reset-density axis uses their schedule control. A thin launcher imports our system (so `@register_system` fires) and drives their runner directly, bypassing their CLI's internal-only filesystem scan.

## 5. Contribution split

- **retention-bench-local** (our repo, depends on `cl-benchmark`): `SubprocessSystem`, the constructive/parametric system(s), reset-axis aggregation, any new constructive-friendly task. This is our named artifact and release cadence.
- **Upstream PRs** (shared primitives): (i) hard-reset / persistence-boundary support if the system-level approach proves too limiting; (ii) entry-point plugin discovery so external packages register without the launcher hack. Both are good-citizen, broadly-useful first PRs.

## 6. Phased roadmap (pre-task; cut into C-series after alignment)

- **C0 — Integration spike.** Stand up a py3.13 env with `cl-benchmark`; run one of their tasks with their ICL system; wrap a trivial echo SUT as `SubprocessSystem` and run it through their runner. Proves the adapter seam end-to-end. *(De-risks everything below.)*
- **C1 — Task triage.** Score their 6 tasks on cross-reset purity + single-shot shape; pick the first target task (or decide we need a new one).
- **C2 — `SubprocessSystem` + hard RESET.** Port `sut_process`/`dir_lifecycle` into the adapter; implement `reset()` as SIGKILL+respawn-from-state_dir; emit `UsageEvent`s.
- **C3 — Constructive system end-to-end.** Wrap `suts/constructive` as a CL-Bench system; run on the C1 task under hard reset; produce a retention curve over `k`.
- **C4 — Reset-axis reporting.** Aggregate gain-vs-`k`; reconcile against their gain metric.
- **C5 — (gate) Outreach.** With a working integration in hand, contact the authors (build-then-offer, per Toby).
- **C6+ — Constructive-friendly task** if triage showed a gap; upstream PRs.

## 7. Disposition of in-flight tasks

- **B4c** (docker/tier, blocked-on-environment) → **DROP** (CL-Bench owns packaging). The thing that was blocking us evaporates.
- **B14** (judge quality), **B16** (boundary token proxy) → **DROP** (CL-Bench owns scoring + cost accounting).

## 8. Open decisions

- **D1.** Confirm §2 architecture direction (adopt-theirs vs keep-ours).
- **D2.** First-target task: pick from their 6 after triage, or build a constructive-friendly one first?
- **D3.** Repo identity: retention-bench keeps its name as "the CL-Bench reset+constructive extension" — agreed?
