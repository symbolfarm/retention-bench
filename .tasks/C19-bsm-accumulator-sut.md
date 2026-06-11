# C19 Keyless BSM accumulator SUT — the offline smoke reference

**Priority:** high
**Blocked by:** nothing
**Touches:** `suts/bsm_accumulator/` (new), `tests/test_bsm_accumulator*.py` (new)

## Context

We are making the **CL-Bench extension the only path** and retiring the legacy
book-track harness (decided this session; see the C18 debrief's "Observations"
for the two-paths framing). The book-track's last remaining justification was
"a fast, offline, keyless sanity check" — `./run.sh smoke`. We confirmed a
CL-Bench-native smoke can be fully offline/keyless:

- the `blind_spectrum_monitoring` (BSM) corpus is byte-deterministic and ships
  git-tracked inside `cl-benchmark` (`retention_bench/bsm_corpus.py`);
- BSM scores **programmatically** (long-run availability IoU in `task.evaluate`)
  — no LLM judge;
- `retention_bench.gain_curve` drives any SUT through CL-Bench's runner with no
  LLM in the driver.

The only missing piece is a **keyless SUT that emits BSM's `ScanReport`**. The
existing `tests/clbench_assets/counter_sut.py` is keyless but emits `{count}`
for a *toy* task, not a `ScanReport`, so it can't drive BSM. The `no_state` /
`notes_llm` / `naive_rag` SUTs need an API key. The `constructive` SUT is
keyless but torch-CPU-trains (a slow "demo", not a 5-second smoke).

This task builds that missing keyless SUT. It is the prerequisite for the
cutover (C20).

## Goal

A small, keyless, dependency-light SUT under `suts/` that speaks the
`SubprocessSystem` contract, emits BSM `ScanReport`s, and **accumulates observed
transmitters in the survive-dir** so that it shows a non-degenerate retention
band (ceiling > stateless prior) when driven through `gain_curve` on the BSM
`default` schedule — fully offline, no API key.

## Acceptance criteria

- [ ] New SUT package (suggested `suts/bsm_accumulator/`, layout mirroring
      `suts/constructive/`: a `<pkg>/clbench_main.py` runnable as
      `python -m bsm_accumulator.clbench_main`). No torch, no network, no key.
- [ ] Per query: reads the new observation, **merges observed transmitters into
      persistent state in the survive-dir** (atomic write *before* the reply so
      it survives the RESET SIGKILL — mirror `counter_sut.py`'s discipline), and
      emits a `ScanReport` from the accumulated persistent set.
- [ ] Reports a `resource` self-report (`flops`/`tokens_in`/`tokens_out`/
      `model_id`) like `counter_sut.py` so `SubprocessSystem`'s `compute`
      UsageEvent accounting has a signal.
- [ ] Driven through `gain_curve` on `blind_spectrum_monitoring` it yields a
      **non-degenerate band**: ceiling `C` (no-reset, state accumulates) >
      stateless prior `P` (wipe-every-reset), and `R(k)` degrades from `C`
      toward `P` as `k` rises. (The whole point is a *legible* retention story.)
- [ ] A test runs the SUT through `gain_curve` on a small `num_instances` BSM
      instance and asserts `C > P` and that a wiped/high-`k` arm scores below the
      ceiling. Keyless — no `OPENROUTER_API_KEY` in the test env.
- [ ] `pytest` passes against the cl-bench 3.13 venv (see TASKS.md for the
      `PYTHONPATH=/workspace .../cl-bench/.venv/bin/python` invocation).

## Relevant files

- `tests/clbench_assets/counter_sut.py` — the keyless SUT pattern to mirror
  (state-in-survive-dir, atomic write before reply, resource self-report).
- `suts/constructive/constructive/clbench_main.py` — the CL-Bench wire
  entrypoint pattern (stdin JSON line in → reply line out; `_iter_requests`).
- `/home/agent/src/cl-bench/src/tasks/blind_spectrum_monitoring/task.py` —
  `ScanReport` / `Transmitter` schema (line ~100), `response_schema` (~1020),
  `step`/`evaluate` scoring (~710).
- `retention_bench/gain_curve.py` — the driver this SUT is built to satisfy.
- `retention_bench/system.py` (`SubprocessSystem`) — the contract.

## Decisions already made

- Path-2-only: this SUT replaces the book-track smoke, it does not supplement it.
- Smoke must be **keyless + offline** — that is the requirement the book-track
  was meeting and this must inherit.
- A *stateful accumulator* (not an empty/naive reporter) is required, because an
  empty `ScanReport` collapses the band (`C ≈ P` → curve excluded) and makes a
  useless smoke.

## Out of scope

- Repointing `./run.sh smoke`, retiring the book-track, doc/README changes — all
  C20.
- Any sophistication beyond "accumulate observed transmitters, report the
  persistent set." It needs to be *just* smart enough to lift `C` above `P`.
- A Dockerfile / pip-installable packaging for this SUT (nice-to-have for
  parity, but the smoke runs it via `--extra-pythonpath`; defer unless trivial).
