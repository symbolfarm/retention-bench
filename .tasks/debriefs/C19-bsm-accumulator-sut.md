# Debrief: C19 Keyless BSM accumulator SUT — the offline smoke reference

**Completed:** 2026-06-11
**Commit:** 2897100

## What shipped

- **`suts/bsm_accumulator/`** — a new stdlib-only reference SUT (package layout
  mirrors `suts/constructive/`: `bsm_accumulator/clbench_main.py`, `pyproject.toml`
  with **no dependencies**, `sut-manifest.json`, `README.md`). It speaks the
  `SubprocessSystem` one-line-JSON contract and drives CL-Bench's
  `blind_spectrum_monitoring` with **no API key and no model weights**.
- **Mechanism:** each query, regex-parse this scan's peaks from the rendered
  prompt, union them into `observed_peaks.json` in the survive-dir (atomic
  `os.replace` flush *before* the reply, so it survives the RESET SIGKILL),
  then emit a `ScanReport` of every transmitter accumulated so far.
- **`tests/test_bsm_accumulator_clbench.py`** — two offline tests
  (`importorskip` on `src.interface`; no torch, no key): a non-degenerate band
  (`ceiling > prior`, `band > 0.03`, not excluded) and perfect retention across
  hard resets (`R(k).mean_reward == ceiling`, `norm_gain == 1.0`,
  `clbench_mean_gain == band` at every k).
- **Measured** (five_ch_wide, seed=42, 20 scans): P=0.2222, C=0.3109,
  band=0.089; R(k)=C at k∈{6,9,19}. Full suite: 127 passed, 1 skipped.

## Design decisions

- **Parse peaks from rendered prose, not structured fields.** `SubprocessSystem`
  forwards only `query.prompt`, not the task's structured `detected_peaks`. The
  `instance.j2` peak lines are stable (`freq: X MHz | power: Y dBm | width: Z
  MHz`), so a single regex is robust. Recorded in the brief's pre-build re-read.
- **Naive union, no interference filter, kept after measuring.** The observation
  model is noisy (`p_miss=0.15`, `p_false_alarm=0.20`, `freq_noise=3.0`) and the
  rendered prompt drops the peak `source`, so the SUT can't filter false alarms
  and jitter spreads a channel across keys. I was prepared to add a
  "seen ≥N times" persistence filter, but **ran the sweep first** — naive
  accumulation already yields a clean positive band (0.089) because the 8 dormant
  channels (invisible to a single-scan prior) dominate the false-alarm cost on
  the wide `five_ch_wide` channels. So I left it naive per the brief's
  "just smart enough / don't over-engineer" guidance.
- **`R(k) == ceiling` is the *intended* shape, not a bug.** Because the
  survive-dir persists through the SIGKILL, a correctly-persisting SUT reloads
  its state and loses nothing across hard resets — the retention band is C (any
  persisting arm) vs the wiped prior P. The test asserts this equality as the
  thesis ("a hard reset with a surviving state-dir loses nothing"), rather than
  expecting a decaying curve.
- **Used `variant=five_ch_wide` (not the `default` schedule)** for both smoke and
  test: 13 channels with no frozen-corpus dependency, fully self-contained.

## Descoped / deferred

- No Dockerfile / pip-install packaging for this SUT (the smoke runs it via
  `--extra-pythonpath`). Per the brief's out-of-scope; add for container parity
  only if needed.
- Absolute scores are low (0.22–0.31) — expected for a deliberately dumb
  accumulator on a noisy task. This is a pipeline/retention smoke, not a quality
  baseline.

## Observations / follow-ups

- **The accumulator is a genuinely good keyless reference**, not just smoke
  scaffolding: it cleanly separates "value of persistence" (C−P) from "value of
  retention across resets" (R(k) vs C), and the latter being flat at the ceiling
  is the cleanest possible illustration of the hard-reset thesis.
- **C20 (the cutover) is unblocked.** It still carries the open decision flagged
  in its brief: disposition of `suts/no_state` + `suts/naive_rag` (recommend
  dropping with the book-track) — awaiting Toby. The smoke command C20 needs is
  proven working in this task's README.

### Filed as tasks

- None new. C20 already filed and was the planned next step.
