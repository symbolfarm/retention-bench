# Debrief: RB-24 Naive-SGD contrast arm at extreme k

**Completed:** 2026-08-28
**Commit:** results in `constructive-retention/notebook/experiments/RB-24-naive-sgd-contrast-arm.md`
(committed there as `d687002`); this repo's record is the run dir + this file.

## Design decisions

- **The reported control stays at `NaiveSGDContinue`'s untouched defaults** (60 steps,
  lr 3e-3), as the brief required. What the brief did not anticipate: at full 64/16
  scale those defaults acquire only **6–31% of the rules** (`rule_acq` 0.062 / 0.312 /
  0.312 per seed), so the arm's low score conflates *forgetting* with *never having
  learned*. The smoke curriculum (4 rules) hit `rule_acq` 1.000 and hid this.
- **So a supplementary 4× budget arm was added** (seed 0, `CONSTRUCTIVE_NAIVE_SGD_STEPS
  =240`), reported separately and explicitly *not* as the control. Rationale: the
  "your baseline was under-trained" objection is the first one a reader raises, and
  answering it costs one 4-minute run. Note the direction — raising the budget can only
  make the control look *better*, so this is not the tuning the brief forbids (which was
  tuning until it degrades). Result: `rule_acq` 0.062 → 0.188, `R` 0.0192 → 0.0529.
  More SGD buys a little acquisition and no retention.
- **Three seeds kept despite observed spread.** The brief said escalate on spread, and
  spread appeared (`R` 0.019 / 0.048 / 0.120, against the constructed arm's exactly
  zero). Not escalated: the contrast is 5–32× the spread and no seed of either arm is
  within range of the other, so more seeds would refine the SGD arm's own mean — which
  is not the question RB-24 asks. The write-up states the spread rather than averaging
  it away.
- **Per-arm SUT stderr archived into the run dir.** `--stderr-log` is on by default but
  writes into each arm's *temp* state dir, which does not survive. The construction line
  (`grad_steps`, `Δbase`, `rule_acq`, hop-1 before→after) is the only in-run evidence
  that the SGD write actually fired, so it is copied to
  `runs/RB-24-2026-08-28/sut-stderr-s{0,1,2}/`. Without it the run record could not
  distinguish "SGD ran and forgot" from "SGD silently no-oped" — the exact failure the
  CR-30 inverted assertions guard against, which deserves evidence in the record and
  not only a guarantee in the code.
- **The write-up went to the sibling repo's notebook** (as the brief's acceptance
  criteria required), while this repo keeps the run dir and this debrief. Same split as
  RB-15, and it is the split that let RB-15 drift: retention-bench owns the measurement
  and must close its own tasks even when the interpretation lives elsewhere.

## Descoped / deferred

- **Mid-range `k` points.** Out of scope by design, and the result vindicates it: the
  SGD arm is flat in `k` including at its own `k=0` ceiling, so no reset density would
  have said anything new.
- **The `RebalancedSGDOracle` ceiling arm.** Still not needed to falsify a flat line;
  it becomes interesting when the question turns from "does construction beat
  forgetting" to "does construction match SGD at parity", which is the North Star
  question and needs a matched-capability design, not another mode.
- **A matched-capability SGD comparison.** Explicitly *not* what this arm is. Anyone
  reading RB-24 as "construction beats SGD" is over-reading it; the write-up says so.

## Observations

- **`R < P` for every seed is the sharpest form of the result** and it breaks the
  metric: the band `C − P` goes negative, so `norm_gain` is undefined and the harness
  prints `[EXCLUDED: < epsilon, curve undefined]`. That is correct behaviour, but note
  that the gain-curve machinery has no way to *report* a below-prior arm other than
  refusing to normalise it. Any future write-up comparing arms should quote raw `R`
  and `clbench_gain` (= `R − P`), which stay meaningful; `norm_gain` silently
  disappears exactly when an arm does worst.
- **`r_max = 0.6154 = 128/208`** is the task's declared maximum (only the 128 probe
  instances are scored; the 80 TRAIN instances score 0). So the constructed arm's
  0.6154 is *literally the task ceiling*, and `P = 0.3077` is exactly half of it —
  every RECALL, zero TRANSFER. Worth stating in any external write-up: the numbers
  look like coincidences and are not.
- **The base cache is shared across arms and keyed with no mode term**, so running the
  constructed arm first makes the SGD arm reuse its exact base. That is what makes the
  comparison point-for-point, and nothing tests it. If someone adds a mode-dependent
  term to `_base_cache_dir`'s key, the arms silently diverge onto different bases and
  the contrast quietly stops being valid.
- The container clock in this session advanced far slower than wall time, which makes
  the timestamps in `runs/RB-24-2026-08-28/` unreliable as durations. The relative
  costs held (~4 min/arm cached).

## Follow-ups

### Filed as tasks

None. RB-24 closes the falsifiability gap RB-15 left; the next open question (M2's
non-overlapping CIs) is a separate, already-known problem and no new work order is
needed to state it.

### Drive-by cleanup landed

- Repaired LOG.jsonl in this repo: `578da87` had written RB-15's debrief and filed
  RB-24 without touching either LOG entry, so RB-15 sat `pending` with its task file
  still present and RB-24 never entered the queue at all.
- Indexed the RB-15 and RB-24 experiment entries in the sibling repo's
  `notebook/INDEX.md` (`2f11f5e`) — RB-15's entry had never been listed.

### Considered and dropped

- Re-running the constructed arm alongside for a same-session comparison. Dropped:
  RB-15's numbers are exact, seed-invariant, and produced by the same code on the same
  base cache. Re-running would spend ~15 minutes to reproduce a constant.
- Filing a task to make `norm_gain` report something for below-prior arms. Dropped as
  premature — the exclusion is arguably correct, and one control arm is not enough
  evidence that the metric needs changing. Noted under Observations instead.
