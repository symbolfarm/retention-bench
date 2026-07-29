# Reference ladder — what the retention metric discriminates

A keyless, offline validity demonstration: the reference SUTs run on a single
task (`symbolic_associative_retention`) so their retention behaviour can be read
side by side. It answers the first question a reviewer asks of any instrument —
*does the headline metric actually separate a system that retains from one that
doesn't?* — and, since RB-16, the second one: *and is it separated from
guessing?*

Regenerate (offline, no API key, no model weights):

```bash
./run.sh ladder
```

This sweeps five keyless reference SUTs over the reset axis
(`--reset-every 1 --reset-every 2`) on the default 112-instance schedule
(`r_max = 64/112 ≈ 0.571`, so `k = 55` and `k = 111` measured resets). Numbers
below were produced this way; they are deterministic, so a re-run reproduces
them exactly.

## The five rungs

| SUT | Mechanism | Prior `P` | Ceiling `C` | `R(k=55)` | `R(k=111)` | Normalised retention `(R−P)/(C−P)` |
|---|---|---:|---:|---:|---:|---:|
| `random_guess` | stateless; uniform guess from the task vocabulary | 0.027 | 0.027 | 0.027 | 0.027 | **EXCLUDED** (band = 0) |
| `no_state` | in-RAM only; never touches the survive-dir | 0.000 | 0.571 | 0.000 | 0.000 | **0.000** |
| `reset_lossy` | geometric forgetting — 1% of recalled facts lost per reset (rate 0.01) | 0.000 | 0.571 | 0.313 | 0.196 | **0.547 → 0.344** |
| `bounded_memory` | FIFO-capped survive-dir window (cap 40) | 0.000 | 0.429 | 0.429 | 0.429 | **1.000** |
| `associative_memory` | full survive-dir persistence | 0.000 | 0.571 | 0.571 | 0.571 | **1.000** |

`R(k)` is identical at `every_1` (k=111) and `every_2` (k=55) for every rung
*except* `reset_lossy` — for the others, retention is reset-count-insensitive
and the discriminator is *mechanism*, not *how many* resets. `reset_lossy` is the
exception by design: it loses a fixed fraction (1%) of its still-recalled facts
on every reset — textbook **geometric/exponential forgetting** — so its retention
*decays with `k`* (the `every_1` arm sits below `every_2`), and it is the only
rung that lands strictly between the floor and the retainers on the normalised
axis.

## The chance line

**Analytic chance is `1/num_attributes = 1/16 = 0.0625` per probe**, or
`0.0625 × r_max = 0.0357` as a run-mean, on the default 16-attribute schedule.
`random_guess` measures `0.027` — one fixed deterministic draw (3 of 64 probes),
which is a sample near, not equal to, the expectation. Both numbers are quoted
because the analytic one is the reference and the measured one is what a rung on
this axis actually looks like.

The rung exists because `no_state`'s honest 0.000 floor invites an equally
honest objection: *your floor SUT declines to answer; a real system would
guess.* It also exists because the chance line used to be **dangerously high**.
Before RB-16 this task's attribute and bin sets were hard-coded pairs, so both
probe families were two-way choices at every schedule size: a constant guesser
scored 0.5 probe-mean, ≈0.308 run-mean — colliding exactly with the then-published
`reset_lossy` `R(k=12) = 0.308`. A coin flip was indistinguishable from the rung
we describe as partial retention. It was not biting empirically only because no
reference SUT guessed; the first LLM measured on that task would have appeared to
retain half of what it was taught while flipping coins. RB-16 widened the probe
space (chance 0.5 → 0.0625) and added this rung so the line is visible rather
than inferred.

`random_guess`'s band is `EXCLUDED` (`P == C == R(k)`) and that is the correct
reading, not a defect: a system with nothing to retain has no normalised
retention. Its job is to place the *raw* `R(k)` line so the other rungs can be
read as above or below chance — `reset_lossy`'s 0.196 at k=111 is ~7× chance,
where before RB-16 the comparable number *was* chance.

## Two readings, two things measured

**Raw score `R(k)` — absolute capability across resets.** The rungs separate
cleanly (`reset_lossy` shown at both reset arms, since it is the one rung whose
raw score moves with `k`):

```
R(k)   0.0 |---------------------------------------| 0.57
random_guess        |=·                                  0.027  (chance)
no_state            ·                                      0.000
reset_lossy (k=111) |=============·                        0.196
reset_lossy (k=55)  |=====================·                0.313
bounded_memory      |=============================·        0.429
associative_memory  |======================================| 0.571
```

**Normalised retention `(R−P)/(C−P)` — did the *learnable band* survive the
resets.** This is the headline metric, and it reads as a graded axis —
**floor → leaky → retainers** — rather than a binary floor-vs-retainers split
(`random_guess` has no band, so it does not appear here):

```
norm   0.0 |---------------------------------------| 1.0
no_state            ·                                      0.000
reset_lossy (k=111) |=============·                        0.344
reset_lossy (k=55)  |=====================·                0.547
bounded_memory      |======================================| 1.000
associative_memory  |======================================| 1.000
```

`reset_lossy` is the rung that makes the headline metric look *graded*: it lands
strictly inside `0 < norm < 1` and, alone among the rungs, *moves down as `k`
grows* (0.547 at k=55 → 0.344 at k=111). It keeps every fact it was taught on
disk but answers a deterministic, shrinking fraction of them after each reset —
so the metric reads degree of retention, not merely its presence.

The key, honest point about the retainers: **`bounded_memory` is capacity-limited,
not reset-lossy.**
Because the task trains all facts before probing, the FIFO cap evicts the oldest
object facts immediately — so the cap lowers `bounded_memory`'s *ceiling* (0.429
vs 0.571), but everything it *can* hold survives every hard reset intact, giving
normalised retention 1.0. It is a fully-retaining system with a smaller box, not
a leaky one.

That is exactly what the headline metric is built to show: normalised retention
**isolates retention fidelity from capacity**. A non-retainer (`no_state`) sits
at the floor (0.0) regardless of how capable it is in a single process (its
ceiling is the full 0.571); the capacity difference between `bounded_memory` and
`associative_memory` shows up in raw `R(k)`, not in retention. An instrument that
conflated the two would rank `no_state`'s 0.571 single-process ceiling above
`bounded_memory` — this one does not.

## Two rungs are calibrated to the schedule

`bounded_memory`'s cap and `reset_lossy`'s rate are **not universal constants**;
they are tuned so each rung lands where its mechanism is legible on *this*
schedule, and RB-16 retuned both when the default schedule changed:

| Knob | Pre-RB-16 | Now | Why |
|---|---|---|---|
| `BOUNDED_MEMORY_CAP` | 8 of 10 trained facts | 40 of 48 | evicts the same one-quarter of object facts; a cap of 8 would keep only trailing rules and collapse the rung onto the floor |
| `RESET_LOSSY_RATE` | 0.05 over 12–25 resets | 0.01 over 55–111 resets | `0.95 ** 111 ≈ 0.003` would have wiped the rung out; `0.99 ** 111 ≈ 0.33` keeps the graded shape |

Re-check both if the task's default width or length changes again.

### Reproducing the pre-RB-16 table

The older published numbers are not orphaned. Passing the pre-RB-16 schedule and
knob values reproduces them exactly (`P = 0.000` / `C = 0.615` throughout;
`no_state` 0.000/0.000, `reset_lossy` 0.308/0.231, `bounded_memory` 0.462/0.462,
`associative_memory` 0.615/0.615 at k=12/k=25):

```bash
RESET_LOSSY_RATE=0.05 BOUNDED_MEMORY_CAP=8 python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --task-kwarg num_attributes=2 --task-kwarg objects_per_attribute=4 \
  --sut "python -m associative_memory.clbench_main" \
  --extra-pythonpath suts/associative_memory \
  --reset-every 1 --reset-every 2 --name legacy-check
```

Those numbers should be *read*, not used: that schedule is the one whose chance
level was 0.308.

## Not yet on the ladder

- **LLM (`notes_llm`) and constructive (`constructive`)** SUTs are deliberately
  excluded here so this figure stays keyless/offline and reproducible without
  credentials or model weights. They extend the same ladder upward. The first
  real LLM measurement is RB-19.
- **Held-out vs bridged transfer.** RB-16 added a never-bridged held-out object
  split, and `evaluate()` reports transfer both ways — but all five rungs here
  compose at *query* time (they persist `object → attribute` and
  `attribute → bin` separately), so bridged and held-out transfer are identical
  for them. The split exists for systems that synthesize `object → bin`
  shortcuts at *write* time, where it is the difference between composing and
  looking up. See `docs/associative-curriculum.md`.
