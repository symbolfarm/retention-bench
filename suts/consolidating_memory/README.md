# consolidating_memory reference SUT

Keyless reference SUT for `symbolic_associative_retention`, and the **variable
rung of the phased store-removal ladder** (see
[`../../docs/phased-store-removal.md`](../../docs/phased-store-removal.md)).

Where [`associative_memory`](../associative_memory/) keeps its whole store in the
survive-dir and [`no_state`](../no_state/) keeps it only in RAM, this SUT does
both at once — which is what the phased protocol requires of a SUT for its
number to mean anything:

- the **episodic buffer** is in RAM and is never written to the survive-dir, so
  a hard RESET destroys it;
- the **consolidated artifact** is a derived map in the survive-dir, written by
  a batch pass over the buffer.

## Knobs

| Variable | Default | Effect |
|---|---|---|
| `CONSOLIDATION_FRACTION` | `1.0` | Fraction of episodes that migrate into the artifact. `0.0` is the floor, `1.0` the ceiling, anything between is a partial rung. |
| `CONSOLIDATION_SELECTOR` | `ordinal` | *Which* episodes migrate: `ordinal` spreads them evenly by arrival order; `hashed` picks them independently by a stable hash of the fact. |
| `CONSOLIDATION_BATCH` | `8` | Episodes buffered before a consolidation pass runs. Anything still pending when the process is killed never migrated. |

All three fail loud on an invalid value rather than falling back to the default,
per the 2026-07-07 review.

## Why consolidation is batched

Because a write-through consolidator is indistinguishable from a store. If every
fact were written to the artifact as it arrived, this SUT would score the ceiling
under *every* reset schedule, exactly like `associative_memory`, and the phased
protocol would have nothing to demonstrate. Batching gives it the property the
protocol exists to detect: episodes still pending at a reset are lost, so the
uniform arm (`--reset-every 1`, buffer never reaches the batch size) reads
`0.000` while the phased arm reads `1.000` on identical machinery. That is the
same signature the real learned SUT shows in the worked example.

## Why `hashed` exists

`symbolic_associative_retention` gives object `i` attribute `i % A`. Under the
`ordinal` selector at fraction 0.5 the migrated objects are exactly the ones
whose attribute rules also migrated, so 2-hop transfer survives at the same rate
as 1-hop recall and `norm_gain` lands on 0.500 — precisely the migration
fraction. That is real, and it is also an artifact of the two structures lining
up. `hashed` breaks the alignment: migration is independent per fact, transfer
survives at roughly the square of the recall rate, and the same fraction scores
0.344. Running both is how the ladder shows which part of the number comes from
the protocol and which from the task's layout.

## Run it

```bash
./run.sh ladder-phased
```
