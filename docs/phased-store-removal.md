# Phased store-removal protocol

A reset can probe two different questions, and conflating them produces
uninterpretable numbers. This doc describes the **phased store-removal** protocol
— a first-class use of `--reset-at` — for the question the uniform retention curve
cannot answer cleanly.

## Two questions a reset can ask

1. **Graceful degradation** — "how well does the system hold task performance as
   working state is erased *repeatedly* across the run?" This is retention-bench's
   headline: the uniform `reset_every_k` retention curve. State erasure is
   interleaved with learning, which is the realistic operating condition.

2. **Migration into the durable artifact** — "after the system has learned, and we
   then *remove its store*, how much capability remains in what persisted?" This is
   the falsifier for *understanding/consolidation* claims: did knowledge migrate
   into the durable artifact (e.g. weights), or was the apparent capability just
   the store being read back?

The uniform curve answers (1). It **cannot** cleanly answer (2): resetting every
`k` instances wipes the store *mid-learning*, so a low `R(k)` conflates "nothing
migrated" with "the store wasn't around long enough to learn from." A system that
consolidates perfectly and one that only reads its store back can both score low,
for opposite reasons.

## The protocol

Run the schedule in two phases and reset **once**, at the boundary:

```
[ learn / consolidate phase ]  →  RESET (store removed)  →  [ probe phase ]
```

Place the single reset at the last learning-phase ordinal with `--reset-at`:

```bash
python -m retention_bench.gain_curve \
  --task <task-with-train-then-probe-schedule> \
  --sut "<launch command>" \
  --reset-at "<train-phase-length>"
```

`R(k=1)` is then measured entirely on the probe phase, with the store gone — so it
reflects only what survived in the durable artifact. Compare it to the ceiling
`C` (no-reset): `R ≈ C` means the capability fully migrated; `R ≈ P` (prior) means
it did not.

### SUT contract for this protocol

Phased store-removal only measures migration if the SUT splits its state correctly:

- the **episodic store** lives in volatile process state (memory), **not** the
  survive-dir, so the hard reset (SIGKILL) removes it;
- only the **consolidated artifact** (e.g. model weights) is checkpointed to the
  survive-dir, so it persists across the reset.

If the SUT persists its raw store to the survive-dir, the reset doesn't remove it
and the protocol degenerates to the store-present condition.

## Worked example — `symbolic_associative_retention`

The schedule is 10 train instances (8 object→attribute facts + 2 attribute→bin
rules), then 8 recall probes (1-hop) and 8 transfer probes (2-hop) — 26 total. The
train/probe boundary is ordinal 10, so the phased run is `--reset-at "10"`.

The learned associative SUT (`constructive-retention --mode associative-learned`)
buffers episodes in memory and checkpoints only weights, satisfying the contract.

```bash
CONSTRUCTIVE_REPLAY_STEPS=60 python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "../constructive-retention/.venv/bin/python -m constructive_retention --mode associative-learned" \
  --reset-at "10" --name learned-phased
```

Result (2026-06-28, `REPLAY_STEPS=60`):

```
  prior   P  = 0.0000
  ceiling C  = 0.3077
    k  schedule        R(k)  norm_gain
    1  boundaries:10  0.3077      1.000
```

`R(k=1) = C` (`norm_gain = 1.000`): the capability the SUT consolidated **fully
survived store removal** — integrated accuracy after the store is deleted equals
the no-reset ceiling. (The ceiling is `0.3077 = 8/26` because 1-hop recall is 8/8
but 2-hop transfer is 0/8 — the composition gap is a separate question. What this
run shows is that whatever *did* integrate survived removal cleanly.) The matching
uniform arm on the same SUT scores `R = 0.0000` (`norm_gain = 0.000`): the
identical model, measured the conflating way, looks like it retained nothing.

The contrast with the uniform arm is the whole point: under `--reset-every 1` the
same SUT collapses to `R ≈ 0` (the buffer is wiped between every train instance,
so earlier facts are never rehearsed), whereas the phased run shows the recall
capability genuinely survived store removal.

## When to use which

| Question | Protocol | Flag |
|---|---|---|
| Graceful degradation across repeated erasure | uniform retention curve | `--reset-every k` |
| Did capability migrate into the durable artifact? | phased store-removal | `--reset-at <train_len>` |
| Sensitivity to *where* a reset lands (drift) | boundary placement | `--reset-at <ordinals>` |

The uniform curve remains retention-bench's headline measurement. Phased
store-removal is the right tool when the claim under test is about consolidation /
understanding migrating into weights, not graceful degradation.
