# RB-19 First real LLM measurement: an agentic (iterative-retrieval) SUT

**Priority:** high
**Blocked by:** RB-16 (measuring on the two-bin task produces numbers that must be discarded)
**Touches:** `suts/` (new agentic-retrieval SUT; possibly `suts/notes_llm/`),
`docs/reference-ladder.md` or a new `docs/llm-snapshot.md`, `README.md` (numbers only)

## Context

From the 2026-07-29 pre-release discussion, where this was identified as the single
highest-value action after the pre-release.

**The instrument has never measured an LLM.** The published reference ladder contains four
synthetic JSON-state programs (`no_state`, `reset_lossy`, `bounded_memory`,
`associative_memory`). The two SUTs involving a real model — `notes_llm` and `constructive` —
were deliberately excluded from the figure to keep it keyless and offline (RB-6).

So the project's headline claim — that chat LLMs and basic LLM agents do not retain — rests on
zero measurements of an LLM. `no_state` is a program written to score zero; it scoring zero
says nothing about any real system. Every claim in the thesis is currently unfalsified in
either direction, and coherence is not evidence.

**Measure the strong version, not a strawman.** A naive single-shot RAG system will fail
multi-hop composition for a structural reason: the query "which bin does <object> go to" has no
lexical overlap with the rule "<attribute> objects go to <bin>", and the join key only appears
*after* the first hop resolves. But an **agentic** system that retrieves twice — attribute
first, then rule — can solve it. That is the system worth measuring. If the instrument only
ever beats naive RAG, nobody should believe it.

The interesting outcomes are both informative:
- Agentic retrieval **passes** composition → the instrument has resolution, the thesis needs
  sharpening, and the interesting failure is somewhere we haven't looked yet.
- Agentic retrieval **fails** → a specific, defensible, non-obvious result.

Either way this measurement tells us more about whether the research direction is right than
another week of design would.

**Reproducibility tier.** This does not join the keyless offline ladder. LLM rungs need keys,
cost money, are nondeterministic, and rot as model IDs are deprecated. Ship the *adapter* (it
is also the reference implementation others copy); publish the *numbers* as a dated snapshot
with pinned model IDs and stored traces, so results stay verifiable as a record after the
model is gone.

## Goal

Produce the project's first measured LLM number on the widened task, published as a dated
snapshot, and record what it implies for the thesis.

## Acceptance criteria

- [ ] An agentic SUT that can issue **more than one** retrieval/lookup against its survive-dir
      before answering. Whether this extends `notes_llm` or is a new SUT is the implementer's
      call — record which and why.
- [ ] Runs through the real `SubprocessSystem` hard-reset path, not an in-process stand-in.
- [ ] Measured on the RB-16 widened task, over the reset axis, with RB-12 bootstrap CIs.
      Small n is acceptable and expected; state it.
- [ ] Model ID pinned and recorded; raw traces stored in-repo so the numbers remain verifiable
      after the model is deprecated.
- [ ] Published as an explicitly **dated snapshot**, visibly separate from the deterministic
      keyless ladder. Do not fold LLM numbers into `reference-ladder.md`'s reproducible table.
- [ ] Written up against the thesis: does iterative retrieval close the composition gap? If it
      does, say so plainly and record what that means for the roadmap.
- [ ] Cost recorded if cheap to capture (tokens at query time). Do **not** block on settling
      the cost metric — that is deliberately unresolved (RB-18, Exploring tier).

## Relevant files

- `suts/notes_llm/` — the existing LLM SUT; candidate base
- `suts/associative_memory/` — the keyless ceiling, for contrast
- `retention_bench/system.py` — `SubprocessSystem`, the real hard-reset path
- `retention_bench/gain_curve.py` — the sweep CLI
- `docs/reference-ladder.md` — the keyless table this must NOT be merged into

## Decisions already made

- **Agentic, not naive.** Naive single-shot RAG is the calibration rung, not the result. Ship
  naive alongside if cheap, but the agentic number is the point.
- **Blocked on RB-16.** On the current two-bin task a guessing LLM scores ≈0.308 run-mean,
  colliding with `reset_lossy`'s published retention figure. Any LLM number taken before the
  widening lands is unusable.
- **Two-tier publication.** Keyless ladder stays the reproducible core that CI runs; LLM
  numbers are a dated snapshot. Ship adapters, not dependencies.
- **Small n is fine.** This is a first measurement to orient the research programme, not a
  leaderboard entry.

## Out of scope

- Claude Code / Codex as SUTs. Their native file-based memory makes them genuinely interesting
  (their memory directory *is* a survive-dir, so testing them isn't handicapping them), but
  they carry their own auth and are not packageable. Document the adapter and publish traces
  in a later task.
- New probe families (revision, aggregation, absence) — roadmap items, not this task.
- Settling the cost metric.
- RB-15 (constructed SUT through the real harness) — separate, and unblocked already.
