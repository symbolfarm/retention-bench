# reset_lossy reference SUT

Keyless JSON-state reference SUT for `symbolic_associative_retention`, the
**graded** rung of the reference ladder — the one that lands strictly between the
no-state floor and the full retainers on the normalised-retention axis.

It mirrors [`associative_memory`](../associative_memory/) — train prompts are
parsed into the survive-dir and recall/transfer probes are answered from it — but
it loses a **deterministic fraction of its answers on each hard reset**, so its
retention *decays with the reset count* `k`. This is the first reference SUT
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
  answered only while `u(fact) < (1 − rate) ** log2(1 + k)`. The threshold is
  monotone-decreasing in `k`, so retention decays smoothly and reproducibly.
- The `log2(1 + k)` damping on the exponent is a deterministic equivalent of the
  brief's suggested raw `(1 − rate) ** k` gate. This task drives 12–25 hard
  resets before the probes run, where a raw per-reset 0.3 loss compounds to total
  wipe-out (`0.7 ** 12 ≈ 0.014`, below every fact's `u`) and collapses the rung
  onto the floor. Damping keeps the properties the rung requires — strictly
  monotone decay in `k`, full reproducibility — while landing the curve in the
  graded band (`0 < norm < 1`).

## The loss rate

- **Default rate: 0.3** (per-reset loss knob; raising it shrinks the answered
  fraction at every `k`).
- Override with the `RESET_LOSSY_RATE` environment variable (a float in
  `[0, 1)`; out-of-range or non-numeric values fall back to the default).

## Run

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m reset_lossy.clbench_main" \
  --extra-pythonpath suts/reset_lossy \
  --reset-every 1 --reset-every 2 --name reset-lossy-graded
```

Expected shape (default rate 0.3): the no-reset ceiling holds the full band
(`C = 16/26 ≈ 0.615`, `k = 0`), and the hard-reset arms decay — `R(every_2)`
(k=12) `= 4/26 ≈ 0.154` (norm 0.250) sits above `R(every_1)` (k=25)
`= 2/26 ≈ 0.077` (norm 0.125). Both land strictly inside `0 < norm < 1`.
