# bsm-accumulator — keyless accumulator reference SUT

The offline, stdlib-only system under test that backs the canonical smoke
(`./run.sh smoke`). It runs Continual Learning Bench's
`blind_spectrum_monitoring` task through `retention_bench.SubprocessSystem` with
**no API key and no model weights** — so the smoke proves the full
reset/retention pipeline end-to-end without network or credentials.

## What it does

Each scan reveals only the *currently active* transmitters' peaks, but the task
scores against *all persistent* transmitters — including ones dormant on the
current scan. So the SUT **accumulates every peak it has seen into the
survive-dir** (`observed_peaks.json`, flushed atomically before each reply so it
survives a hard-reset SIGKILL) and reports the full accumulated set every scan.

That makes the retention band legible:

- **Ceiling `C`** (state accumulates, no reset) — recovers dormant transmitters
  seen on earlier scans → reported occupancy matches ground truth → high IoU.
- **Stateless prior `P`** (survive-dir wiped each reset) — only ever sees the
  current scan's active subset → over-claims available spectrum → low IoU.
- **`R(k)`** degrades from `C` toward `P` as hard resets accumulate.

## Run it

```bash
# Through the gain-curve driver (what ./run.sh smoke calls):
python -m retention_bench.gain_curve \
  --task blind_spectrum_monitoring \
  --task-kwarg variant=five_ch_wide \
  --sut "python -m bsm_accumulator.clbench_main" \
  --extra-pythonpath suts/bsm_accumulator \
  --reset-every 1 --reset-every 2
```

`variant=five_ch_wide` (5 active + 8 dormant channels) needs no frozen corpus, so
the run is fully self-contained.

## Non-goals

It is not a detector: it does no signal processing and cannot distinguish genuine
channel peaks from interference (the rendered prompt drops the peak `source`).
It is deliberately *just smart enough* to make the retention signal legible — the
real systems (in-context `notes_llm`, constructive parametric) live elsewhere.
