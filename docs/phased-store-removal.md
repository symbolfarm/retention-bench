# Phased store-removal protocol

A reset can probe two different questions, and conflating them produces
uninterpretable numbers. This doc describes the **phased store-removal** protocol
— a first-class use of `--reset-at` — for the question the uniform retention curve
cannot answer cleanly.

## Two questions a reset can ask

1. **Graceful degradation** — "how well does the system hold task performance as
   working state is erased *repeatedly* across the run?" The uniform
   `reset_every_k` retention curve. State erasure is interleaved with learning,
   which is the realistic operating condition.

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

The current default schedule is 48 train instances (32 object→attribute facts +
16 attribute→bin rules), then 32 recall probes (1-hop) and 32 transfer probes
(2-hop) — 112 total. The train/probe boundary is ordinal 48, so the phased run is
`--reset-at "48"`.

The learned associative SUT (`constructive-retention --mode associative-learned`)
buffers episodes in memory and checkpoints only weights, satisfying the contract.

> The `--sut` command needs an **absolute** interpreter path. The SUT is spawned
> with its own working directory, so a path relative to the retention-bench root
> will not resolve.

```bash
CONSTRUCTIVE_REPLAY_STEPS=60 python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "/abs/path/to/constructive-retention/.venv/bin/python -m constructive_retention --mode associative-learned" \
  --reset-at "48" --name learned-phased-48
```

Result (2026-08-02, `REPLAY_STEPS=60`, default 112-instance schedule):

```
  prior   P  = 0.0000  [0.000,0.000]
  ceiling C  = 0.2857  [0.196,0.375]
    k  schedule        R(k)  95% CI        norm_gain  95% CI            n
    1  boundaries:48  0.2857 [0.196,0.375]     1.000  [0.643,1.538]   112
```

`R(k=1) = C` (`norm_gain = 1.000`): the capability the SUT consolidated **fully
survived store removal** — integrated accuracy after the store is deleted equals
the no-reset ceiling.

The ceiling is `0.2857 = 32/112` because 1-hop recall is 32/32 but 2-hop transfer
is 0/32 — the composition gap is a separate question. What this run shows is that
whatever *did* integrate survived removal cleanly.

The matching uniform arm on the same SUT and schedule:

```bash
# ... same --sut, with:  --reset-every 1 --name learned-uniform-48
    k  schedule   R(k)  95% CI        norm_gain  95% CI          n
  111  every_1  0.0000 [0.000,0.000]      0.000  [0.000,0.000]  112
```

The contrast is the whole point: the identical model, measured the conflating way,
looks like it retained *nothing*. Under `--reset-every 1` the buffer is wiped
between every train instance, so earlier facts are never rehearsed and the SUT
never gets to consolidate at all — whereas the phased run shows the recall
capability genuinely survived store removal.

> **On the interval.** `norm_gain`'s CI (`[0.643, 1.538]`) is a percentile
> bootstrap over 112 per-instance outcomes and is wide. It supports "migration
> happened"; it does not finely quantify how much. Read the point estimate as a
> verdict, not a measurement.
>
> This example is one real SUT, not a calibrated ladder. Unlike the uniform sweep
> (see [`reference-ladder.md`](reference-ladder.md)) there is no keyless floor,
> chance, or partial-consolidation rung run through this protocol, so the protocol
> is *argued* to discriminate rather than *demonstrated* to. Building that ladder
> is open work.

## When to use which

| Question | Protocol | Flag |
|---|---|---|
| Graceful degradation across repeated erasure | uniform retention curve | `--reset-every k` |
| Did capability migrate into the durable artifact? | phased store-removal | `--reset-at <train_len>` |
| Sensitivity to *where* a reset lands (drift) | boundary placement | `--reset-at <ordinals>` |

Neither protocol is *the* headline. Pick by the claim being made: phased
store-removal when the claim is about consolidation / understanding migrating into
the durable artifact, the uniform curve when it is about graceful degradation under
repeated erasure. The instrument's central claim (see
[`../README.md`](../README.md)) is a consolidation claim, so phased store removal is
the protocol that bears on it most directly — but the keyless reference ladder is
currently calibrated on the uniform sweep only, and a phased ladder does not exist
yet. Reporting either without saying which question it answers is how the two get
conflated.
