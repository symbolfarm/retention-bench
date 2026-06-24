# RB-7 Reset-lossy reference SUT — the graded normalised rung

**Priority:** medium
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `suts/reset_lossy/**`, `tests/test_reset_lossy_clbench.py`, `run.sh`, `docs/reference-ladder.md`, `README.md`

## Context

RB-6 built the reference ladder and surfaced an honest gap (see
`docs/reference-ladder.md` "Not yet on the ladder" and the RB-6 debrief): on the
**normalised retention** metric `(R−P)/(C−P)`, the current reference set only
separates *floor vs retainers* — `no_state` reads 0.0, every retainer reads 1.0.
`bounded_memory` is **capacity-limited, not reset-lossy** (its FIFO cap lowers the
*ceiling*, but everything it holds survives every reset), so it too reads 1.0.

There is no SUT that loses *some but not all* of its learnable band **across the
reset itself** — i.e. nothing lands strictly between 0 and 1 on the normalised
axis. That is the rung that makes the headline metric look *graded* rather than
binary, which matters for the C17 public narrative (we want to show the metric
measures degree of retention, not just presence).

## Goal

A keyless, deterministic `reset_lossy` reference SUT that persists to the
survive-dir but drops a fraction of its retained state on each hard reset, so its
retention **decays with `k`** and its normalised retention lands strictly between
0 and 1. Wire it into the ladder so the figure gains the graded rung.

## Acceptance criteria

- [ ] `suts/reset_lossy/` mirrors `suts/associative_memory/` structure (package +
      `clbench_main.py`, `pyproject.toml`, `sut-manifest.json`, `README.md`).
- [ ] Retention is **graded and deterministic**: `0 < normalised_retention < 1`,
      and `R(k)` *decreases* as `k` grows (so the `every_1` arm sits below the
      `every_2` arm — it will be the first reference SUT where reset-count matters).
- [ ] Loss rate is a small default (e.g. **0.3**), env-overridable
      (`RESET_LOSSY_RATE`); document default + override.
- [ ] Runs keyless/offline through gain_curve on `symbolic_associative_retention`.
- [ ] Added to `./run.sh ladder` (as a rung between floor and the retainers) and
      to the `docs/reference-ladder.md` table + bars, with the committed numbers
      regenerated. Update the doc's "Not yet on the ladder" note (this fills it).
      Mention it in the README reference-SUT list.
- [ ] `tests/test_reset_lossy_clbench.py` drives the SUT through `SubprocessSystem`
      and asserts decay across resets (more resets → fewer facts recalled), with a
      fixed seed/rate so the assertion is deterministic.
- [ ] Full suite green: `.venv/bin/python -m pytest`. `scripts/promote.sh dryrun` clean.

## Relevant files

- `suts/associative_memory/` — persistence template.
- `suts/no_state/`, `suts/bounded_memory/` — the existing rungs.
- `docs/reference-ladder.md`, `run.sh` (the `ladder` subcommand), `README.md`.
- `tests/test_associative_memory_clbench.py` — test template.

## Decisions already made

- **Deterministic decay, not random per-run.** The ladder figure must reproduce
  exactly. Suggested mechanism: persist the full fact set plus a load counter
  (incremented each process start, so it tracks resets survived); assign each fact
  a stable pseudo-uniform value `u(fact) ∈ [0,1)` via a fixed hash, and *answer*
  only facts with `u(fact) < (1 − rate)^k` where `k` is resets-survived. This is
  monotone-decreasing in `k`, fully deterministic, and yields a graded curve.
  Implementer may choose an equivalent deterministic scheme — the requirement is
  reproducibility + decay with `k`, not this exact formula.
- **Target task `symbolic_associative_retention`** — same as the rest of the ladder.
- **Keyless/offline.**

## Out of scope

- Cutting public `main` (C17).
- LRU / other eviction policies — this is about *reset-coupled* loss, distinct
  from `bounded_memory`'s capacity cap.
