# reset_lossy reference SUT

Keyless JSON-state reference SUT for `symbolic_associative_retention`, the
**graded** rung of the reference ladder — the one that lands strictly between the
no-state floor and the full retainers on the normalised-retention axis.

It mirrors [`associative_memory`](../associative_memory/) — train prompts are
parsed into the survive-dir and recall/transfer probes are answered from it — but
it loses a **fixed fraction of its still-recalled facts on each hard reset**
(geometric/exponential forgetting), so its retention *decays with the reset count*
`k`. This is the first reference SUT
where the number of resets matters: the `every_1` arm (more resets) sits below
the `every_2` arm.

This is distinct from [`bounded_memory`](../bounded_memory/): that SUT's FIFO cap
lowers its *ceiling* but lets everything it holds survive every reset intact
(normalised retention 1.0). `reset_lossy` keeps every fact it was taught on disk,
yet answers fewer of them after each reset — capacity-independent, reset-coupled
loss.

## Deterministic decay mechanism

- The survive-dir holds the full fact set (`reset_lossy.json`, never pruned) plus
  a `load_count` that is incremented and persisted once per process start. A
  fresh run starts the process once (`load_count == 1`); each hard reset
  SIGKILLs the process and the runner respawns it, bumping the counter. So
  `k = load_count - 1` is exactly the number of resets the on-disk state has
  survived when a probe is answered.
- Each fact gets a stable pseudo-uniform value `u(fact) ∈ [0, 1)` from a fixed
  BLAKE2b hash of its identity (no per-run randomness, no seed file). A fact is
  answered only while `u(fact) < (1 − rate) ** k`. This is textbook **geometric
  (exponential) forgetting**: a constant fraction `rate` of the still-recalled
  facts is dropped on each hard reset, so the answered fraction is `(1 − rate) ** k`
  after `k` resets — monotone-decreasing, fully deterministic, and reproducible.
  Because retention is a genuine exponential in `k`, `R(k)` traces a real decay
  curve.

## The loss rate

- **Default rate: 0.01** (per-reset loss fraction — "loses 1% of recalled facts
  per reset"). It is deliberately *small*: this task drives 55–111 hard resets
  before its probes, so a large per-reset rate compounds to a total wipe-out
  (e.g. `0.7 ** 55 ≈ 3e-9`) and collapses the rung onto the floor. A small rate
  keeps the curve in the graded band (`0 < norm < 1`) with an honest
  interpretation.
- **The rate is tuned to this task's reset count, not a universal constant.** It
  was 0.05 against the pre-RB-16 26-instance schedule (12–25 resets); RB-16
  widened the task to 112 instances, and `0.95 ** 111 ≈ 0.003` would have
  collapsed the rung onto the floor. At 0.01 the survivor fraction is
  `0.99 ** 55 ≈ 0.57` / `0.99 ** 111 ≈ 0.33`. Re-check it if the task's default
  schedule length changes again.
- Override with the `RESET_LOSSY_RATE` environment variable (a float in
  `[0, 1)`; out-of-range or non-numeric values raise rather than falling back).

## Run

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m reset_lossy.clbench_main" \
  --extra-pythonpath suts/reset_lossy \
  --reset-every 1 --reset-every 2 --name reset-lossy-graded
```

Expected shape (default rate 0.01): the no-reset ceiling holds the full band
(`C = 64/112 ≈ 0.571`, `k = 0`), and the hard-reset arms decay — `R(every_2)`
(k=55) `= 35/112 ≈ 0.313` (norm 0.547) sits above `R(every_1)` (k=111)
`= 22/112 ≈ 0.196` (norm 0.344). Both land strictly inside `0 < norm < 1`, and
both sit well above the measured chance line (`suts/random_guess`, 0.027).
