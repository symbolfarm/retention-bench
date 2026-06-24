# Reference ladder — what the retention metric discriminates

A keyless, offline validity demonstration: the reference SUTs run on a single
task (`symbolic_associative_retention`) so their retention behaviour can be read
side by side. It answers the first question a reviewer asks of any benchmark —
*does the headline metric actually separate a system that retains from one that
doesn't?*

Regenerate (offline, no API key, no model weights):

```bash
./run.sh ladder
```

This sweeps three keyless reference SUTs over the reset axis
(`--reset-every 1 --reset-every 2`). Numbers below were produced this way; they
are deterministic, so a re-run should reproduce them exactly.

## The three rungs

| SUT | Mechanism | Prior `P` | Ceiling `C` | `R(k)` | Normalised retention `(R−P)/(C−P)` |
|---|---|---:|---:|---:|---:|
| `no_state` | in-RAM only; never touches the survive-dir | 0.000 | 0.615 | 0.000 | **0.000** |
| `bounded_memory` | FIFO-capped survive-dir window (cap 8) | 0.000 | 0.462 | 0.462 | **1.000** |
| `associative_memory` | full survive-dir persistence | 0.000 | 0.615 | 0.615 | **1.000** |

(`R(k)` is identical at `every_1` (k=25) and `every_2` (k=12) for all three —
retention here is reset-count-insensitive; the discriminator is *mechanism*, not
*how many* resets.)

## Two readings, two things measured

**Raw score `R(k)` — absolute capability across resets.** The three rungs separate
cleanly:

```
R(k)   0.0 |---------------------------------------| 0.62
no_state           ·                                       0.000
bounded_memory     |==============================·        0.462
associative_memory |======================================| 0.615
```

**Normalised retention `(R−P)/(C−P)` — did the *learnable band* survive the
resets.** This is the headline metric, and it separates **floor vs retainers**:

```
norm   0.0 |---------------------------------------| 1.0
no_state           ·                                       0.000
bounded_memory     |======================================| 1.000
associative_memory |======================================| 1.000
```

The key, honest point: **`bounded_memory` is capacity-limited, not reset-lossy.**
Because the task trains all facts before probing, the FIFO cap evicts the two
oldest facts immediately — so the cap lowers `bounded_memory`'s *ceiling* (0.462
vs 0.615), but everything it *can* hold survives every hard reset intact, giving
normalised retention 1.0. It is a fully-retaining system with a smaller box, not
a leaky one.

That is exactly what the headline metric is built to show: normalised retention
**isolates retention fidelity from capacity**. A non-retainer (`no_state`) sits
at the floor (0.0) regardless of how capable it is in a single process (its
ceiling is the full 0.615); the capacity difference between `bounded_memory` and
`associative_memory` shows up in raw `R(k)`, not in retention. A benchmark that
conflated the two would rank `no_state`'s 0.615 single-process ceiling above
`bounded_memory` — this one does not.

## Not yet on the ladder

- **A reset-lossy rung** — a SUT that retains *some but not all* of its band
  *across each reset* (e.g. probabilistic survive-dir corruption per reset) would
  populate a middle point on the *normalised* axis (0 < norm < 1), distinct from
  `bounded_memory`'s capacity limit. Candidate future reference SUT.
- **LLM (`notes_llm`) and constructive (`constructive`)** SUTs are deliberately
  excluded here so this figure stays keyless/offline and reproducible without
  credentials or model weights. They extend the same ladder upward.
