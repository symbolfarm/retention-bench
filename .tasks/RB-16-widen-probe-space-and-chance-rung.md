# RB-16 Widen the probe space, add a chance-level rung, re-measure the ladder

**Priority:** high
**Blocked by:** nothing
**Touches:** `retention_bench/tasks/symbolic_associative_retention.py`, `suts/` (new
`random_guess` reference SUT), `tests/test_symbolic_associative_retention.py`,
`tests/test_scoring.py`, `docs/reference-ladder.md`, `docs/associative-curriculum.md`,
`docs/metrics.md`

## Context

Found during Toby's pre-release read of `retention_bench/tasks/symbolic_associative_retention.py`
(2026-07-29 session).

`_ATTRIBUTES = ("red", "blue")` and `_BINS = ("bin-a", "bin-b")` are fixed at length 2, and
`attr_for` assigns `self._ATTRIBUTES[i % len(self._ATTRIBUTES)]`. So **regardless of
`num_concepts` (1–12), both probe families are two-way choices.** A SUT that answers `red`
to every RECALL and `bin-a` to every TRANSFER scores 0.5 probe-mean → ≈0.308 run-mean on the
default schedule.

That number collides exactly with `reset_lossy`'s published `R(k=12) = 0.308` in
`docs/reference-ladder.md` — i.e. **a constant guesser is indistinguishable from the rung we
describe as partial retention.** It is not biting empirically today only because `no_state`
declines to answer rather than guessing (it floors at 0.000), so the measured ladder is
honest as-published. But the moment a real LLM SUT is measured it *will* guess, and the table
would appear to show an LLM retaining half of what it was taught when it is flipping coins.

This is a correctness bug that blocks every number in the pre-release, and it blocks RB-19
(first LLM measurement) specifically — measuring an LLM on the two-bin task would produce
numbers that have to be thrown away.

Second, smaller problem with the same root cause: with only 2 bins the TRANSFER probe is not
really testing composition. Knowing the attribute is binary gives you the bin without ever
consulting the taught rule. TRANSFER is the probe that carries the project's in-context-
generalization claim, so it needs to be genuinely two-hop.

Prior art in the sibling repo: constructive-retention hit this and fixed it the same way —
CR-9 widened to 16 attrs / 64 objects explicitly "to de-noise the held-out-transfer estimate",
and CR-23 later gave each attribute/bin a distinct single ASCII byte to kill a shared-first-
char confound. Do **not** copy CR's single-byte alphabet here: RB's task is read by LLM and
JSON-state SUTs where nonce *words* are the right surface form. Only the width is being
adopted.

## Goal

Make the guessing floor unambiguous: parametrise the attribute/bin sets so chance level is
low, add an explicit `random_guess` reference rung so the chance line is visible rather than
inferred, and re-measure `docs/reference-ladder.md` at the new width.

## Acceptance criteria

- [ ] `SymbolicAssociativeRetentionTask` takes a `num_attributes` argument; `_ATTRIBUTES` and
      `_BINS` are generated to that width rather than hard-coded pairs. Nonce words, not
      single bytes.
- [ ] Default `num_attributes` chosen and justified in the docstring (see "Decisions" —
      16 unless the objects-per-attribute maths argues otherwise).
- [ ] `num_attributes=2` still reproduces the current schedule exactly, so the existing
      published numbers remain regenerable.
- [ ] `r_max` continues to be computed per concrete schedule in `build_canonical_run_state()`
      (RB-13 behaviour preserved); the stale class-attribute default is updated to match the
      new default schedule and its comment kept accurate.
- [ ] New `suts/random_guess/` reference SUT: keyless, offline, deterministic under a seed,
      answers uniformly at random from the task's attribute/bin vocabulary.
- [ ] `docs/reference-ladder.md` re-measured at the new default width, with `random_guess`
      added as an explicit rung and the analytic chance level stated in prose.
- [ ] `docs/associative-curriculum.md` and `docs/metrics.md` updated for the new default
      (both currently quote `r_max = 16/26` and the 8-concept/2-attribute shape).
- [ ] `pytest` green from a clean checkout.

## Relevant files

- `retention_bench/tasks/symbolic_associative_retention.py` — the generator; `_ATTRIBUTES`,
  `_BINS`, `_build_instances`, `build_canonical_run_state`
- `tests/test_symbolic_associative_retention.py` — incl. the `r_max` per-schedule test
- `suts/no_state/`, `suts/associative_memory/` — templates for the new `random_guess` SUT
- `docs/reference-ladder.md` — the table being re-measured
- `docs/associative-curriculum.md` — the task spec; quotes the old shape
- `docs/metrics.md` — quotes `r_max = 16/26` in the ε discussion

## Decisions already made

- **Widen, don't switch to single-byte symbols.** CR uses one distinct ASCII byte per
  attribute/bin because its SUTs are tiny char-level models where multi-char names create
  tokenization/keying confounds. RB's SUTs are LLMs and JSON-state programs reading prompts,
  where nonce words are the natural surface. Adopt CR's *width*, not its alphabet.
- **Keep `num_attributes=2` reproducible.** The published ladder numbers must stay
  regenerable so the pre-release doesn't orphan its own history.
- **Add the chance rung rather than only documenting chance analytically.** "`no_state`
  scores zero" invites "your floor SUT declines to answer". A measured guessing rung answers
  that directly, and it is cheap.
- **Default width target ≈16** (chance ≈0.06), mirroring CR-9. The implementer should sanity-
  check the interaction with `num_concepts`: with `num_concepts=8` and 16 attributes most
  attributes have no object, which may make the attribute→bin rules mostly untested. Either
  raise the default `num_concepts` or pick a width that keeps ≥2 objects per attribute —
  **this is the one genuinely open design call in the task; record what you chose and why.**

## Out of scope

- Any new probe family (revision, aggregation, absence) — those are v0.2 roadmap items,
  filed separately after RB-18.
- Graded/distance-based scoring — needed for aggregation probes later, not for this task.
- Measuring any LLM SUT — that's RB-19, which this task unblocks.
- Touching `blind_spectrum_monitoring` or any upstream CL-Bench task.
