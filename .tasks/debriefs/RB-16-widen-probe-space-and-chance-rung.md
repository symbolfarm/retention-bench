# Debrief: RB-16 Widen the probe space, add a chance-level rung, re-measure the ladder

**Completed:** 2026-07-29
**Commit:** `647d3c6` (task + SUT + tests), `ca81d54` (docs + re-measured ladder)

## What shipped

`symbolic_associative_retention` is parametrised by width and carries a held-out
composition split; the ladder has a measured chance rung and has been
re-measured at the new default.

- **Width.** `num_attributes` (default **16**) replaces the hard-coded
  `("red","blue")` / `("bin-a","bin-b")` pairs. Chance drops from 0.5 per probe
  (0.308 run-mean — the number that collided with `reset_lossy`'s published
  `R(k=12)`) to 1/16 = 0.0625 per probe / 0.0357 run-mean. Nonce words, not CR's
  single-byte alphabet.
- **Held-out split**, mirroring constructive-retention's `composition_bijection`:
  `objects_per_attribute` (default 2) × `num_attributes` objects, last
  `num_attributes` of them held out of *bridging* (one per attribute, each with a
  bridged exemplar earlier). Held-out objects still get their TRAIN instance, so
  RECALL stays fair. TRAIN `object_attribute` prompts and query metadata carry
  `role: bridge|holdout`; instance metadata carries `held_out`.
- **`evaluate()`** reports `transfer_bridged_mean_reward` /
  `transfer_heldout_mean_reward` / `num_transfer_*` / `chance_level`, and the
  summary line leads with held-out vs bridged.
- **`_OBJECT_NAMES` 12 → 48** nonce names; `_ATTRIBUTES` 2 → 20 (first two are
  `red`/`blue`, in position, for reproduction); `_BINS` generated `bin-a`…`bin-t`.
- **New `suts/random_guess/`** — keyless, offline, stateless, deterministic under
  `RANDOM_GUESS_SEED`, uniform over the task vocabulary, wired into `./run.sh
  ladder` as the first rung.
- **`docs/reference-ladder.md` re-measured** from an actual `./run.sh ladder`
  run; `associative-curriculum.md`, `metrics.md`, `phased-store-removal.md`,
  `README.md`, `docs/README.md`, `scoring.py` and two SUT READMEs updated.

### Re-measured ladder (default schedule: 112 instances, `r_max = 64/112 ≈ 0.571`)

| SUT | `P` | `C` | `R(k=55)` | `R(k=111)` | norm |
|---|---:|---:|---:|---:|---:|
| `random_guess` | 0.027 | 0.027 | 0.027 | 0.027 | EXCLUDED (band = 0) |
| `no_state` | 0.000 | 0.571 | 0.000 | 0.000 | 0.000 |
| `reset_lossy` (rate 0.01) | 0.000 | 0.571 | 0.313 | 0.196 | 0.547 → 0.344 |
| `bounded_memory` (cap 40) | 0.000 | 0.429 | 0.429 | 0.429 | 1.000 |
| `associative_memory` | 0.000 | 0.571 | 0.571 | 0.571 | 1.000 |

Analytic chance: **0.0625 per probe, 0.0357 run-mean**. The rung measures 0.027
(3 of 64 probes) because it is one fixed deterministic draw, not an expectation;
both numbers are in the doc.

### Reproduction of the pre-RB-16 numbers — verified

`--task-kwarg num_attributes=2 --task-kwarg objects_per_attribute=4` with
`RESET_LOSSY_RATE=0.05 BOUNDED_MEMORY_CAP=8` regenerates the published table
exactly: `P = 0.000`, `C = 0.615`, and `no_state` 0.000/0.000, `reset_lossy`
0.308/0.231, `bounded_memory` 0.462/0.462, `associative_memory` 0.615/0.615 at
k=12/k=25. There is a covering unit test
(`test_legacy_two_attribute_schedule_is_reproducible`) plus the command in
`docs/reference-ladder.md`.

### Verification

`.venv/bin/python -m pytest` from the repo root: **154 passed, 2 skipped**
(baseline before the task: 137 passed, 2 skipped). Ladder re-measured with
`./run.sh ladder` (~38s).

## Descoped / deferred

Nothing from the brief. Out-of-scope items (new probe families, graded scoring,
LLM measurement, `blind_spectrum_monitoring`) were left alone.

## Design decisions

- **Signature: `objects_per_attribute`, not `num_concepts`.** The brief left this
  open. `num_concepts` is **gone** rather than derived: with a held-out split the
  meaningful degrees of freedom are *how many attributes* and *how many objects
  share each one*, and a surviving `num_concepts` would have been a third knob
  that can silently contradict the other two (a non-multiple leaves an attribute
  without a bridged exemplar). Object count is `num_attributes ×
  objects_per_attribute`, exposed read-only as `self.num_objects`. Cost: the
  legacy schedule is now spelled `num_attributes=2, objects_per_attribute=4`
  rather than defaulting; that spelling is tested and documented.
- **Default `objects_per_attribute = 2`**, giving 32 objects / 16 held out — the
  minimum satisfying the ≥2 invariant, and it matches CR's held-out n=16 (CR gets
  there with 64 objects / 4 per attribute, i.e. more *bridged* exemplars per
  attribute, not more held-out ones). Chose the smaller schedule because RB's
  runtime is dominated by process-kill resets: at 112 instances the ladder is 38s
  and the test suite went 43s → 98s; 4 objects/attribute would have been 208
  instances and roughly doubled that again for no gain in the held-out estimate.
- **48 `_OBJECT_NAMES`** (brief asked for ≥32). 48 leaves headroom for
  `objects_per_attribute=3` at the default width without another naming pass.
- **Attribute vocabulary keeps `red`/`blue` in positions 0–1**, with 18 nonce
  words after. Slightly inelegant, but it is what makes `num_attributes=2`
  reproduce the old prompts byte-for-byte instead of merely shape-for-shape.
- **`role:` is added to TRAIN prompts unconditionally**, including in the legacy
  configuration, so the legacy prompts differ from the pre-RB-16 ones by that one
  line. No reference SUT parses it, so every legacy *number* still reproduces;
  the alternative (suppressing the line when nothing is held out) would have made
  the prompt format schedule-dependent.
- **Retuned two reference SUTs that the brief did not mention.** Both were
  calibrated against the old 26-instance schedule and would have collapsed onto
  the floor:
  - `bounded_memory` `DEFAULT_CAP` **8 → 40**. 48 facts are trained now; a cap of
    8 keeps only the trailing rules, so recall and transfer both go to 0 and the
    capacity rung becomes a second floor. 40 evicts the 8 oldest object facts —
    the same one-quarter the old pairing evicted.
  - `reset_lossy` `DEFAULT_RATE` **0.05 → 0.01**. The reset count went from 12–25
    to 55–111, and `0.95 ** 111 ≈ 0.003` is a wipe-out. At 0.01 the survivor
    fraction is `0.99 ** 55 ≈ 0.57` / `0.99 ** 111 ≈ 0.33`, preserving the graded
    shape. Both knobs now carry a "calibrated to the schedule, re-check on
    change" note in code, README and the ladder doc.
- **`random_guess` carries the task vocabulary rather than learning it.** A
  guesser that accumulated vocabulary from TRAIN prompts would need to *persist*
  it to answer after a reset, which would give it a non-zero band and a
  normalised retention of 1.0 — a chance rung reading as a perfect retainer.
  Hardcoding the vocabulary (with a drift test pinning it to the task's tuples)
  makes `P == C == R(k)`, so the band is EXCLUDED and the rung does only its
  actual job: placing the raw chance line.
- **It guesses within the correct probe family** (attributes for RECALL, bins for
  TRANSFER) rather than over the union. That is the *stronger* guesser, so the
  chance line it draws is the conservative one.
- **Determinism is per-prompt** (`blake2b(seed ‖ prompt)`), not a stateful RNG,
  so the rung is flat across arms and survives process kills without state.

## Observations

- **The bug was worse than "chance is high".** Because the two-way task made
  `reset_lossy`'s rate-0.05 curve land exactly on the constant-guesser score, the
  ladder's graded rung and its chance level were the *same number*. Widening
  alone would not have made that legible — retuning the rate was needed for the
  rung to stay graded at all under the longer schedule, and the chance rung was
  needed to show the separation. Three coupled changes, one bug.
- **Reset count, not just width, is a calibration parameter.** Anything tuned
  against this task's *length* (rather than its content) breaks when the default
  schedule changes. Both reference-SUT knobs were in that class and neither was
  flagged in the brief. Worth remembering before the next schedule change.
- **Runtime.** The suite went 43s → 98s, almost entirely process-kill resets in
  the five SUT sweeps (each `--reset-every 1` arm now restarts the SUT 111 times).
  Still fine for always-on tests, but a further widening should buy the estimate
  something specific.
- The held-out split is currently unobservable on this repo's own rungs: every RB
  reference SUT composes at query time, so bridged and held-out transfer are
  identical for all five. The split only bites for write-time-bridging systems
  (CR's bridging mode) — this is documented in both the curriculum doc and the
  ladder doc so nobody reads "held-out == bridged" as a validation.

## Follow-ups

### Filed as tasks

None. RB-19 (first LLM measurement) is the natural consumer and is already
queued; it is now unblocked.

### Drive-by cleanup landed

- `TASKS.md`'s RB-16 bullet flipped to done with a one-line summary of the
  outcome, and RB-17 marked unblocked (`ca81d54`).
- `retention_bench/scoring.py`'s docstring example (`r_max = 16/26`) and
  `tests/test_scoring.py`'s illustrative constant updated to the new default
  (`647d3c6`, `ca81d54`).

### Considered and dropped

- Reporting *recall* split by bridged/held-out as well as transfer: recall is a
  1-hop lookup for both groups by construction, so the split carries no signal
  there. `held_out` is on every probe's metadata, so a post-hoc analysis can
  still do it.
- A CR-style `SCHEDULE_FINGERPRINT` assertion: CR needs one because its
  curriculum is *duplicated* across two venvs. RB has a single definition, so a
  fingerprint would only restate the existing schedule tests.
