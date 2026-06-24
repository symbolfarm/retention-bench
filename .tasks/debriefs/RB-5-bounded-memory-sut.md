# Debrief: RB-5 Bounded-memory reference SUT — the partial-retention rung

**Completed:** 2026-06-24
**Commit:** 45fc5ed

## What shipped

A keyless, offline `bounded_memory` reference SUT under `suts/bounded_memory/`,
mirroring `associative_memory`: `bounded_memory/__init__.py` +
`bounded_memory/clbench_main.py`, `pyproject.toml`, `sut-manifest.json`,
`README.md`, plus `tests/test_bounded_memory_clbench.py`.

It answers the same `symbolic_associative_retention` TRAIN/RECALL/TRANSFER
protocol as `associative_memory` and persists state to the survive-dir with the
same atomic write (`tmp` + `os.replace`), but it persists only a **capped FIFO
window** of the most recent facts. Facts pushed out of the window by newer facts
are evicted and fail recall/transfer, so retention is *partial*.

Implementation note: where `associative_memory` keeps two unbounded dicts, this
SUT keeps a single ordered list of fact entries (`{kind, key, value}`), oldest
first. The FIFO is **global across both fact kinds** (object->attribute facts and
attribute->bin rules) — every stored fact counts against the same window. Store
re-inserts a refreshed fact at the most-recent end, then evicts from the front
until `len <= cap`.

### The cap

- **Default cap: 8.** Overridable via env var `BOUNDED_MEMORY_CAP` (any int
  `>= 1`; non-numeric / `< 1` falls back to the default). Manifest declares the
  env var; README documents the default + override.

### Task fact count vs cap

`symbolic_associative_retention` (default config) trains **10 facts**: 8
object->attribute facts (`norb, tave, luma, zek, pim, dax, vosh, mip`, alternating
red/blue) followed by 2 attribute->bin rules (`red->bin-a`, `blue->bin-b`). It then
poses 16 scored probes (8 RECALL + 8 TRANSFER).

10 trained facts > cap 8, so eviction is visible without any tuning — the default
cap of 8 was kept. The two oldest object facts (`norb`, `tave`) fall out of the
window. The 2 rules are trained last, so they survive; this means only the 2
evicted objects' RECALL and TRANSFER probes fail:

- RECALL: 6/8 survive (norb, tave evicted)
- TRANSFER: 6/8 survive (norb, tave attrs gone; rules intact for the rest)
- Total probes: 12/16 -> whole-run mean reward 12/26.

### Partial-retention curve numbers (gain_curve, keyless/offline)

Command (exactly the acceptance-criteria command):

```
.venv/bin/python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m bounded_memory.clbench_main" \
  --extra-pythonpath suts/bounded_memory \
  --reset-every 1 --reset-every 2 --name bounded-memory-partial
```

```
  prior   P  (stateless baseline) = 0.0000
  ceiling C  (no-reset, k=0)      = 0.4615   (= 12/26)
  band    C - P                   = 0.4615

    k  schedule        R(k)     norm_gain  clbench_gain   n
   12  every_2         0.4615   1.000      0.4615         26
   25  every_1         0.4615   1.000      0.4615         26
```

### Lands strictly between floor and ceiling — confirmed

- RB-4 floor (`no_state`):           R(k) = 0.0000
- **RB-5 partial (`bounded_memory`): R(k) = 0.4615 (= 12/26)**
- Full retainer (`associative_memory`): R(k) = 0.6154 (= 16/26)

Verified the ceiling reference by running `associative_memory` myself this
session: it reports C = R(k) = 0.6154. So `0 < 0.4615 < 0.6154` — partial, not
floor, not full.

Subtlety worth recording: because all 10 facts are trained *before* any probe,
the eviction already bites at k=0, so the bounded SUT's own no-reset *ceiling* is
the capped 0.4615 (not the full 16/26). R(k) then holds at that capped ceiling
across resets because the on-disk window survives the SIGKILL. The "partial"
property is therefore best read against the *full retainer's* ceiling (16/26),
which is exactly how the reference ladder will plot the three rungs.

## Tests

`tests/test_bounded_memory_clbench.py` (3 tests, all green):

1. `test_bounded_memory_partial_retention_band` — sweep ceiling == 12/26 and
   strictly `0 < ceiling < 16/26`.
2. `test_bounded_memory_retains_window_across_resets` — every reset arm holds the
   capped ceiling (state survives the hard reset; not the floor).
3. `test_bounded_memory_evicts_oldest_fact_across_reset` — drives the SUT through
   `SubprocessSystem` with `BOUNDED_MEMORY_CAP=2`, trains three facts, hard-resets,
   then asserts the oldest is `unknown` while the two recent ones survive. This is
   the direct eviction assertion the AC asks for.

Full suite: **75 passed, 2 skipped**. `scripts/promote.sh dryrun`: clean (leak
check OK).

## Descoped / deferred

Followed the task's "Out of scope" exactly: no reference-ladder figure, no
README/`run.sh` reference-SUT-list edits (RB-6), no container/Dockerfile, no
non-FIFO eviction policies. All edits stayed inside `suts/bounded_memory/**` +
`tests/test_bounded_memory_clbench.py`.

## Design decisions

- **Single global FIFO across both fact kinds** rather than a per-kind cap. The
  task brief pre-decided "FIFO eviction at a small cap"; a global window is the
  simplest reading and makes eviction depend on total recency, which is what a
  bounded scratchpad would actually do. A per-kind cap would have needed two caps
  and a less legible story.
- **Default cap kept at 8** — the task's standard fact count (10) already exceeds
  it, producing visible eviction (2 facts dropped) without tuning. No adjustment
  needed.
- **`model_id` / manifest `name` = `bounded-memory`** (hyphen), package
  `bounded_memory` (underscore), matching the `associative_memory` /`no_state`
  convention. Distinct state filename (`bounded_associations.json`) so the
  on-disk schema (an ordered list, not two dicts) can't be confused with the full
  retainer's.
- **Atomic write preserved verbatim** (`tmp` + `os.replace`) — the only behavioural
  addition over the template is the FIFO cap, as the task specified.
- **`flops` resource scales with `len(state)`** (capped), so the bounded SUT
  self-reports a smaller, bounded compute/storage footprint than the full
  retainer — a nice secondary signal for the ladder if reported later.

## In-flight observations

- The gain_curve driver owns survive-dir isolation; the partial behaviour comes
  entirely from the SUT's cap, no harness cooperation.
- `BOUNDED_MEMORY_CAP` propagates to the subprocess because `spawn_sut` launches
  with `os.environ.copy()`, so `monkeypatch.setenv` in the eviction test reaches
  the SUT cleanly.

## Follow-ups (candidate, not filed)

- **RB-6 ladder figure** should plot all three rungs (0 / 12/26 / 16/26) on one
  axis vs the full-retainer band (16/26); the numbers above are the inputs.
- A second bounded point at a *different* cap (e.g. cap=4 -> more eviction) would
  give the ladder a fourth, lower partial rung essentially for free via the env
  var — worth considering for the figure if a single partial point looks thin.

### Considered and dropped

- Sharing prompt-parsing with `associative_memory` via a helper module. Dropped
  for the same reason as RB-4: each reference SUT is intentionally self-contained
  (own `pyproject.toml`, launched via `--extra-pythonpath`), and the divergence
  *is* the point of the ladder.
