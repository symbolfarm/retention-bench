# Debrief: C2 Productionize SubprocessSystem + reset schedule + compute accounting

**Completed:** 2026-06-07
**Commit:** 572ee98

## What shipped

A `retention_bench` package that turns the C0 spike into production code:

- `retention_bench/system.py::SubprocessSystem(ContinualLearningSystem)` —
  wraps an arbitrary subprocess SUT, reusing `harness.sut_process` spawn/kill
  and `harness.dir_lifecycle.account_dir` verbatim. `respond()` maps a CL-Bench
  `Query` → JSONL request → `query.response_schema`; `reset()` is a hard process
  bounce keeping the survive-dir.
- `retention_bench/reset_schedule.py` — `NoReset` / `EveryNInstances(n)` /
  `ExplicitBoundaries({...})`, a `ResetSchedule` Protocol. Density is driven from
  `observe()` (count instance-complete boundaries, self-bounce), independent of
  the runner's `reset_between_instances` boolean.
- Compute accounting: `call_type="compute"` `UsageEvent`s — one per `respond()`
  carrying SUT-self-reported FLOPs/tokens, one per instance boundary carrying the
  survive-dir storage delta (bytes/files/reset-flag).
- `retention_bench/_clbench.py` — the single chokepoint for the `src.*` import.
- `pyproject.toml` — `cl-benchmark` pinned as a GitHub VCS dep `@9cc63c0`;
  `requires-python` bumped to `>=3.13`; `retention_bench*` added to packages.
- `tests/test_subprocess_system.py` + `tests/clbench_assets/counter_sut.py` —
  7 tests through the real runner and direct usage-event drive. All pass on 3.13;
  the module `importorskip`s cleanly on the 3.12 venv.

## Descoped / deferred

- **Wrapping real reference SUTs** (no_state/notes_llm/naive_rag/constructive)
  is C3+. C2 ships the adapter and a contract-speaking test SUT only.
- **Trace/curve reporting** of the compute + retention signal is C4. C2 emits the
  events; nothing consumes them into a report yet.
- **Network-installed dep verified at runtime**: the pinned `git+https` dep is
  declared but the dev loop runs against the existing editable `cl-benchmark` in
  `/home/agent/src/cl-bench/.venv` (no re-clone). A clean `pip install` from the
  VCS URL into a fresh 3.13 venv was not exercised.

## Design decisions

- **Bumped `requires-python` to `>=3.13` + hard `cl-benchmark` dep** (confirmed
  with Toby) rather than isolating the dep in an optional extra to preserve the
  3.12 legacy suite. Rationale: the legacy book-track SUTs need contract rework
  to run under CL-Bench anyway (their `READ`/`QUIZ`→`answers` shape can't carry a
  per-query `response_schema`), so freezing the 3.12 world buys nothing. Pleasant
  surprise: the full existing suite runs **green on 3.13** (87 passed, 3 skipped),
  so the migration didn't actually break the carried-forward pieces.
- **Did NOT reuse `harness.sut_process.send_event`.** It hard-codes the
  book-track `event_type` + `answers:[{id,text}]` framing, which can't express
  CL-Bench's arbitrary `response_schema`. The brief's reuse target is the
  *process lifecycle* (spawn/kill) — and the spike already used its own framing.
  C2 defines a CL-Bench-shaped JSONL contract (`prompt` + `response_schema` →
  `action` + optional `resource`) on top of `spawn_sut`/`kill_sut`.
- **Two compute events per instance, separated by `metadata.kind`**
  (`"respond"` vs `"storage"`). FLOPs/tokens live only on respond events; storage
  events carry no token fields, so a naive token sum across all compute events is
  still correct. A FLOPs consumer must filter `kind=="respond"`.
- **Reset boundaries keyed by 1-based completed-instance ordinal**, not
  `Query.instance_index`. The ordinal is dense/monotonic; `instance_index` is a
  canonical id a shuffled/subset run may deliver out of order. Documented in
  `reset_schedule.py`.
- **Kept `wipe_on_reset`** from the spike as the stateless-baseline arm (clears
  the survive-dir on each bounce). Not in the brief's criteria, but it's a few
  lines and lets the adapter produce both arms of CL-Bench's `mean_gain` and the
  retention-discrimination test; cheap and useful for C4.
- **`reset()` emits no usage event.** The runner drains and discards events from
  the start-of-run `reset()` (runner.py:239-241), so emission belongs to
  `respond()`/`observe()` only; `reset()` and the scheduled bounce share a
  private `_hard_bounce()` that does the kill/respawn without recording.

## Observations

- **The runner hard-resets once at startup** (`reset_system=True` default →
  `system.reset()` before the first query). `reset()` must therefore be safe with
  no handle yet (no-op bounce) — easy to miss; the spike got away with it only
  because of the `if self._handle is not None` guard.
- **The 3.13 venv had neither pip nor pytest.** Installed pytest via
  `uv pip install --python .venv/bin/python pytest`. Worth knowing for future
  CL-Bench-side test runs.
- **Storage delta is measured in `observe()` *before* the bounce** — the SIGKILL
  can't change on-disk state, and the survive-dir already holds the instance's
  final writes at that point, so this is the correct measurement point.

## Follow-ups

### Considered and dropped

- *File a "verify clean `pip install` from the pinned VCS URL" task.* Dropped —
  it's a one-liner to fold into C3's environment setup (C3 needs a real 3.13
  install anyway to wire the constructive SUT). Re-raise only if C3 hits friction.
- *File a "C7: upstream a first-class reset-density hook" task.* Already covered —
  C7 exists and the brief/C0 already record it as a nice-to-have, not a blocker.
