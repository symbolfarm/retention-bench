# C1 — CL-Bench task triage

**Status:** decided. **Date:** 2026-06-07. **Task:** C1.
**Feeds:** C3 (which task the constructive system runs on), C6 (whether we
need to build a new task — we don't).
**Context:** [`clbench-pivot-plan.md`](clbench-pivot-plan.md),
[[project_clbench_pivot]], [[project_toby_research_frame]].

## Question

CL-Bench ships six tasks. Which one do we target first with our single-shot
SUT contract + hard-RESET + constructive system — or do we need to build a
new one (C6)? Scored on three axes:

- **(a) Cross-reset purity** — does reward *require* state carried across
  instances, so wiping the survive-dir on a hard reset measurably drops
  reward? (This is the framework's `mean_gain` = stateful − stateless
  baseline; a task with high gain has a load-bearing retention signal.)
- **(b) Shape** — within one instance, is it single-shot (one `respond()` →
  terminal outcome) or multi-step-agentic (`step()` loops, returning
  `next_query` with `done=False` for several tool/SQL/action turns)? Our SUT
  contract is single-shot (C0); multi-step needs a contract extension.
- **(c) Understanding-vs-stenography** — can a verbatim notepad of past
  observations score well, or does reward require generalizing to genuinely
  new instances (the episodic→understanding transfer signal)?

## Scoring

| Task | (a) cross-reset purity | (b) shape | (c) understanding signal | `r_max` / n |
|---|---|---|---|---|
| **blind_spectrum_monitoring** | **High** — accumulated latent occupancy map *directly* drives the IoU reward; memoryless agent reasons from scratch each scan | **Single-shot** ✓ | **High** — must *infer* hidden persistent channel structure from noisy, gappy scans (transmitters vanish for many scans); not memorizable | 1.0 / 20 |
| exploitable_poker | High — opponent model is only learnable across hands; one hand is informatively near-blind; profit-over-time | Multi-step (one action/turn per hand) | Med–High — notepad of past hands helps, but new cards demand a generalized opponent model | 9.49 / 50 |
| sales_prediction | Med–High — "limited data retention" *forces* reliance on carried institutional knowledge + persisted workspace code | Multi-step (bash turns + 2-phase submit) + Docker | High — must learn growth dynamics / store lifecycles and extrapolate to future years | 1.0 / 12 |
| cohort_studies | Medium — epidemiological patterns transfer across heterogeneous schemas, but each study is largely scorable from its own DB | Multi-step (SQL + 2-phase submit) | High — statistical reasoning across coding-convention drift | 0.162 / sched |
| database_exploration | Med–High — schema knowledge cuts exploratory queries; **but** reward is *efficiency only* — a wiped system stays correct, just slower | Multi-step (QUERY/ANSWER loop) | **Low–Med** — schema is fixed; a "table X has columns Y" notepad largely suffices → stenography-friendly | 1.0 / 30 |
| codebase_adaptation | Medium — repo knowledge transfers as fewer steps, but reward is confounded by per-issue difficulty; Docker | Multi-step (bash turns) + Docker | High — must comprehend code, not memorize | 1.0 / 15 |

## Recommendation: **blind_spectrum_monitoring** as the first target

The decision is nearly over-determined by shape: **it is the only single-shot
task in the suite** — every other task loops `step()` within an instance
(bash commands, SQL QUERY/ANSWER cycles, poker actions, or a two-phase
submission handshake). It therefore runs through CL-Bench's real runner against
our existing single-shot SUT contract **with zero contract extension** (verified:
`task.py:710` — one `ScanReport` `respond()` → `_handle_report` →
`_advance(instance_complete=True)`, one `InstanceOutcome` per scan).

And it is not merely the least-bad single-shot option — it is also **strong on
the two axes that matter for our contribution**:

- **Cross-reset purity (a) is high and clean.** The reward (IoU between true
  long-run available spectrum and the reported map) rises only as the system
  accumulates occupancy structure across scans. A hard reset with an empty
  survive-dir forces re-inference from scratch → a sharp, legible reward drop.
  That is exactly the retention-vs-`k` curve we exist to produce.
- **Understanding signal (c) is high.** The latent channel structure is stable
  but hidden; the system must *infer* it from noisy, intermittent observations,
  not transcribe them. A notepad of raw scans is weak because transmitters
  "disappear for many scans before returning" — you have to model persistence.
  This is a clean episodic→understanding-transfer probe ([[project_toby_research_frame]]).

It is also a **good fit for a constructive/parametric learner**: inferring a
stable latent occupancy map from streaming noisy evidence is precisely the kind
of function a small growing model can hold in weights — letting us contrast a
parametric system against the notepad/ICL baselines on a task where the carried
state is a *learned function*, not a fact store ([[project_constructive_transformers]]).

### One nuance to carry into C3/C4 — concept drift

The task injects **concept drift via schedule-stage transitions** (different
stages reference variants with different channel configs; ground truth is the
union of persistent channels across stages). This means the retention curve
over `k` may be **non-monotonic**: a reset that lands on a drift boundary can
*help* by clearing a stale occupancy belief, while a reset mid-stage purely
hurts. This is a feature, not a bug — it gives C4 a richer story (retention is
not uniformly "more memory = better"; *when* you reset interacts with drift).
C2's explicit-boundary reset schedule should let us place resets on vs. off
drift boundaries deliberately to expose this.

## Do we need to build a new task (C6)?

**No — C6 is not triggered as a blocker.** blind_spectrum_monitoring fits the
single-shot contract and is strong on purity + understanding + constructive-
friendliness. C6 (a constructive-friendly task) stays an *optional* backlog
item, not a prerequisite for C3.

## Tasks needing the SUT contract extended to in-instance turns

All five non-spectrum tasks require multi-step support before we can target
them: **codebase_adaptation, cohort_studies, database_exploration,
exploitable_poker, sales_prediction**. The extension is an *adapter/loop*
change, not a contract change — the JSONL channel already supports N
round-trips against one process handle (pivot-plan §3); the SUTs just need to
emit intermediate actions and consume `observe()` feedback within an instance.

**Natural second target (once multi-step lands): `exploitable_poker`.** Highest
cross-reset purity of the multi-step set (the opponent model is *only*
acquirable across hands), a clean continuous profit reward, a deterministic
opponent (so the signal isn't washed out by environment noise), and no Docker
dependency. It is the strongest constructive showcase after spectrum. The two
Docker-backed tasks (codebase, sales) are lowest-priority first contact — they
add a packaging surface CL-Bench owns but that complicates our reset (process
kill vs. container lifecycle). database_exploration is de-prioritized on axis
(c): its efficiency-only reward is the most stenography-friendly of the six.
