# no_state reference SUT — the retention floor

Keyless, **ephemeral** reference SUT for `symbolic_associative_retention`. This is
the **floor** of the reference ladder: a SUT that learns within an episode but
retains nothing across a hard RESET.

It answers the same TRAIN/RECALL/TRANSFER protocol as `associative_memory`, with
one deliberate difference: memory is held **only in-process**, in a plain in-RAM
dict that lives for the lifetime of the Python process. It has no
`_load_state`/`_save_state` and **never reads or writes the survive-dir**
(`RETENTION_BENCH_DIR`).

## Why ephemeral (in-RAM) rather than truly stateless?

A truly stateless SUT (fresh state per request) would produce a flat floor line
at the prior `P` everywhere, including `k=0`. Keeping within-process memory
instead makes the curve *drop*: recall is high at `k=0` (within-episode learning
holds, because the dict survives across requests in the same process) and
collapses to `P` for `k>=1` (each hard RESET kills the process, and since nothing
was persisted the next process boots empty). That drop is more informative than a
flat line — it visually demonstrates exactly what the benchmark measures: the
hard RESET erases un-persisted working state.

## Run

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m no_state.clbench_main" \
  --extra-pythonpath suts/no_state \
  --reset-every 1 --reset-every 2 --name no-state-floor
```

Expected shape: the no-reset ceiling `C` is above the wiped stateless prior `P`
(within-episode learning is real), but every stateful arm with `k>=1` reset sits
at the floor `P` (`R(k) ≈ P`, normalised gain ≈ 0), because no state survives the
process kill.
