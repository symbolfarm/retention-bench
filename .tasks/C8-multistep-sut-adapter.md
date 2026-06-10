# C8 Multi-step (turn-taking) SUT adapter for agentic CL-Bench tasks

**Priority:** low
**Blocked by:** C2
**Touches:** `retention_bench/`, `harness/sut_process.py`, `docs/sut-interface.md`, `suts/`

<!-- Deferred-but-tracked. Sequenced AFTER the single-shot retention curve
     (C3/C4) ships. C2 is the hard prerequisite because this extends the
     SubprocessSystem wire schema. -->

## Context

C1 triage ([`docs/archive/clbench-task-triage.md`](../docs/archive/clbench-task-triage.md))
picked **blind_spectrum_monitoring** as the first target precisely because it
is the *only* single-shot task in CL-Bench — one `respond()` → terminal
`InstanceOutcome`. **All five other tasks** (codebase_adaptation,
cohort_studies, database_exploration, exploitable_poker, sales_prediction) are
**multi-step-agentic**: CL-Bench's runner calls `system.respond(query)`
repeatedly *within one instance*, feeding the previous step's observation back
via `query.feedback`, until the task returns `done=True` (e.g. several SQL
queries per DB question, several actions per poker hand). Targeting any of them
requires this adapter.

The pivot plan (§3) called this "an adapter/loop change, not a contract
change." C1's wrap-up refined that as **too optimistic**: the *transport* is
free, but the *message schema* and the *SUT's behaviour* are real work (see the
three layers below). This task captures that refinement so the implementer of
target #2 doesn't rediscover it cold.

This is the gating work for the **second target task**, recommended in the
triage doc as **`exploitable_poker`** (highest cross-reset purity of the
agentic set, clean continuous profit reward, deterministic opponent, no
Docker).

## Goal

Extend `SubprocessSystem` + the SUT wire contract so a SUT can act as a
turn-taking agent within one CL-Bench instance — emit a non-terminal action,
consume the resulting observation as feedback, and continue — driven by
CL-Bench's existing per-instance `respond()`/`step()` loop. Demonstrated on one
agentic task (poker, unless re-triaged).

## The three layers (where the work actually is)

1. **Transport — already done, no work.** The SUT is a long-lived process with
   persistent stdin/stdout JSONL framing; `SUTHandle` survives N `send_event`
   round-trips. The runner calling `respond()` k times within one instance = k
   `send_event`s against one live process. Reuse as-is.
2. **Wire schema — generalize (a real, modest contract change).** Today
   `send_event` hardcodes a two-word vocabulary: event types `READ`/`QUIZ`,
   reply keys `stage_output`/`answers`, and it *validates* a QUIZ reply carries
   an `answers` list (`harness/sut_process.py:268`). CL-Bench queries instead
   carry an arbitrary `prompt` + a pydantic `response_schema` + optional
   `feedback`. Generalize the framing to "here is a prompt, a JSON schema to
   conform to, and feedback on your last action; reply with matching JSON."
   Update `docs/sut-interface.md` in lockstep.
3. **SUT behaviour — the real cost (per-SUT, not in the adapter).** A
   multi-step SUT must become turn-taking: (a) detect instance boundaries (when
   `instance_complete` flips / `instance_id` changes) to know when to clear
   per-instance scratch vs. carry it; (b) consume `query.feedback` to choose
   its next action; (c) hold intra-instance working state across `respond`
   calls. The runner owns the outer loop, so no loop driver is needed in the
   SUT — but the act→observe→act behaviour is. **For the constructive SUT this
   is a genuine design decision:** does it do a weight update on every
   intra-instance observation, or only at the instance boundary? Decide and
   document.

   *Confound to watch:* agentic tasks reward **efficiency** (`reward = 1 −
   regret/budget`, regret = turns taken; poker = profit), so turn-by-turn
   behaviour directly moves the score — more surface to get subtly wrong than a
   single-shot accuracy reward.

## Acceptance criteria

- [ ] `send_event` / the SUT wire format generalized from the fixed
      `READ`/`QUIZ` vocabulary to arbitrary `prompt` + `response_schema` +
      `feedback`; `docs/sut-interface.md` updated to match.
- [ ] `SubprocessSystem.respond()` maps a multi-step `Query` (with `feedback`)
      → SUT action → `query.response_schema`, across k turns of one instance,
      with the SUT process held live across turns.
- [ ] At least one SUT (the echo/counter test SUT) drives an agentic task
      through the real runner to `done=True`, asserting the intra-instance turn
      count and that feedback reached the SUT.
- [ ] The constructive SUT's intra-instance learning policy (per-step vs.
      per-instance-boundary update) is decided and documented.
- [ ] A run on the second target task (poker, unless re-triaged) completes and
      emits a `TaskResult`.

## Relevant files

- `docs/archive/clbench-task-triage.md` (why this is deferred; second-target choice)
- `harness/sut_process.py` (`send_event`, the wire framing to generalize)
- `docs/sut-interface.md` (the contract doc to update in lockstep)
- `retention_bench/` (the C2 `SubprocessSystem` to extend)
- `/home/agent/src/cl-bench/src/interface.py` (`Query.feedback`,
  `Observation.instance_complete`, the `respond`/`step` loop)
- `/home/agent/src/cl-bench/src/tasks/exploitable_poker/task.py` (first consumer)

## Decisions already made

- D (2026-06-07): single-shot first (blind_spectrum); this multi-step work is
  deliberately deferred until after the single-shot retention curve (C3/C4)
  ships. Filed now — rather than left in the triage doc — so the detail reaches
  the implementer via the just-in-time task-brief channel, not a doc no one is
  routed to reopen.
- Second target is `exploitable_poker` unless re-triaged (C1 recommendation).

## Out of scope

The single-shot pipeline (C2/C3/C4). A new constructive-friendly task (C6).
Wrapping the Docker-backed agentic tasks (codebase, sales) — lowest priority;
their container lifecycle complicates the hard-reset (process-kill) story.
