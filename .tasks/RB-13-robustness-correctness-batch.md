# RB-13 Robustness & correctness batch (sweep leak, stderr, fail-loud knobs, taxonomy)

**Priority:** medium
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `retention_bench/gain_curve.py` (`run_reset_sweep`, CLI), `harness/sut_process.py`
(`spawn_sut` stderr), the reference SUTs' env-var parsing, `retention_bench/system.py`
(`_split_reply`, `SubprocessSystem.__init__`), `retention_bench/tasks/symbolic_associative_retention.py`,
`suts/*/sut-manifest.json`, `tests/test_docker_launch.py`

## Context

The smaller findings from review 2026-07-07 — each real, each small, batched so they land in
one pass rather than five. `run_reset_sweep`'s missing context manager was verified against
`gain_curve.py:179` (bare `system = make_system(...)`, no `with`, despite the class shipping
one to avoid leaking the final container).

## Goal

Close the low-severity correctness/ergonomics gaps that make the harness leak resources, hide
SUT diagnostics, or silently run the wrong experiment.

## Acceptance criteria

- [ ] **Sweep uses the context manager:** `with make_system(...) as system:` in
      `run_reset_sweep` (`gain_curve.py:~179`) so the final container/subprocess per arm can't
      leak under GC delay or exception.
- [ ] **`--stderr-log` exposed and defaulted on** into the per-arm state dir (`spawn_sut`
      currently `DEVNULL`s SUT stderr, so a crashing SUT in a sweep yields only "closed stdout
      before replying" with diagnostics discarded — the first thing a SUT author needs).
- [ ] **Env-var knobs fail loud:** `RESET_LOSSY_RATE`, `BOUNDED_MEMORY_CAP` (and peers) raise
      on invalid values instead of silently falling back to defaults — for a *benchmark*, a
      typo'd parameter silently running the default is worse than a crash.
- [ ] **`_split_reply` error taxonomy:** `reply.get("resource") or {}` must not coerce falsy
      non-dict values into `{}`; a schema-nonconforming `action` should surface as `SUTError`,
      not a raw pydantic `ValidationError`, so errors are consistent at the contract boundary.
- [ ] **`r_max` computed per instance-schedule** in `build_canonical_run_state` rather than a
      stale class attribute (`16/26` is wrong for `num_exposures=2` → `16/36`). Blast radius is
      CL-Bench-side aggregates only (retention-bench measures `C`), but fix it at the source.
- [ ] **`.harness/` dir-creation parity:** `SubprocessSystem.__init__` creates the reserved
      dir that `dir_lifecycle.create_dir` does (the two paths have drifted).
- [ ] **Book-track dead code** (review architecture gripe 1 — added 2026-07-17; code removal,
      so it lives here rather than in RB-14's doc-only sweep): remove the dead `send_event`
      (`harness/sut_process.py:223`) — not trivially deletable, `tests/test_docker_launch.py:159`
      still calls it, so either rewrite that test against the live `_exchange` path or demote
      `send_event` to a test helper — and drop the legacy `entrypoint` field from the
      `suts/*/sut-manifest.json` files + its handling in `spawn_sut` (the live path uses the
      system `command`; `retention_bench/system.py:85–89` documents that `entrypoint` names the
      retired book-track module).

## Decisions already made

- **One batch, not six tasks** — these are individually trivial and touch overlapping files.

## Out of scope

- `torch.load(weights_only=False)` in `checkpoint.load` — note-only for now (own survive-dir);
  revisit if survive-dirs ever become shared/auditable artifacts (an ACE vector then).
- The `sut_kit` reference-SUT de-duplication — deferred; borderline at 4 copies, revisit at 6.
