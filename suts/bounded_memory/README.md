# bounded_memory reference SUT

Keyless JSON-state reference SUT for `symbolic_associative_retention`, the
**partial-retention** rung of the reference ladder.

It mirrors [`associative_memory`](../associative_memory/) — train prompts are
parsed into the survive-dir and recall/transfer probes are answered from it — but
it persists only a **capped FIFO window** of the most recently trained facts.
Facts pushed out of the window by newer facts are evicted and fail recall, so
retention is *partial*: its gain curve sits visibly between the `no_state` floor
(`R(k) = 0`) and a full retainer (`associative_memory`, `R(k) = C`).

## The cap

- **Default cap: 40 entries.** The window is global across both fact kinds
  (object->attribute facts and attribute->bin rules); every stored fact counts
  against the same FIFO window, ordered by insertion / most-recent overwrite.
- Override with the `BOUNDED_MEMORY_CAP` environment variable (any integer
  `>= 1`; non-numeric or `< 1` values raise rather than falling back).

`symbolic_associative_retention` (default config) trains **48 facts** (32
object->attribute facts followed by 16 attribute->bin rules). With the default
cap of 40 the 8 oldest object facts (`norb` … `mip`) are evicted, so their recall
and transfer probes fail while the rest survive a reset — visible partial
retention.

**The cap is calibrated to the task's default schedule.** It was 8 against the
pre-RB-16 10-fact schedule; RB-16 widened the task to 16 attributes / 32 objects,
and a cap left at 8 would have kept only trailing rules and collapsed this rung
onto the floor. 40 evicts the same one-quarter of object facts the old pairing
did, so the rung keeps its shape (`ceiling` strictly between the floor and the
full retainer, normalised retention 1.0). Re-check it if the task's default width
changes again.

## Run

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m bounded_memory.clbench_main" \
  --extra-pythonpath suts/bounded_memory \
  --reset-every 1 --reset-every 2 --name bounded-memory-partial
```

Expected shape: `R(k)` is clearly above the stateless prior (`P = 0`) but clearly
below the full-retainer ceiling (`C = 64/112`), because `bounded_associations.json`
survives process kills but only carries the most recent `cap` facts.
