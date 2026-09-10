# Debrief: RB-21 Phased store-removal reference ladder

**Completed:** 2026-09-10
**Commit:** e7d8832 (SUT + `run.sh`), b51ea8e (tests), dd2fe3e (docs), b013f3f (notebook)

## Design decisions

- **The brief's first rung was wrong, and finding out was the task's main
  result.** It specified a rung that *"persists its raw store to the survive-dir
  — after removal should collapse to ~`P`"*. Under the actual reset semantics
  (SIGKILL, survive-dir kept) that SUT loses nothing, so it scores the *ceiling*,
  not the floor. The brief's second sentence had it right — it doubles as the
  contract-violation control — but a control that scores 1.000 identically to
  genuine consolidation is a much stronger finding than a floor rung, and it is
  why every rung now runs both arms. The floor role went to the consolidating SUT
  at fraction 0.0, which holds mechanism constant across the whole ladder.
- **One parameterised SUT, not three packages.** The brief described three rungs
  as three behaviours. They are three settings of one behaviour, and the ladder's
  claim is that it varies *migration* with everything else held constant — three
  packages would have made that claim unverifiable by construction.
- **Consolidation is a batch pass, not a write-through.** A write-through
  consolidator is behaviourally a store: it would score the ceiling on every
  schedule, exactly like `associative_memory`, and the ladder would demonstrate
  nothing. Batching (default 8 episodes) gives the rung the property the protocol
  exists to detect — pending episodes are lost at a kill — and reproduces the
  worked example's `1.000` phased / `0.000` uniform signature without a model.
- **Two partial rungs, because the first number was too pretty.** Fraction 0.5
  scored exactly `0.500`. That is an artifact: the task assigns object `i`
  attribute `i % A`, so an every-other-episode selector migrates exactly the
  objects whose rules it also migrated and 2-hop transfer tracks 1-hop recall
  instead of compounding. The `hashed` selector (independent per fact) scores
  `0.344` on the same fraction. Both are in the ladder so the number cannot be
  read as "half the capability migrated".
- **No chance rung was added.** The brief asked to confirm rather than assume:
  `random_guess` is degenerate under this protocol (`P == C == 0.0268`, band
  EXCLUDED on both arms). It stays in the run as a visible confirmation, not as a
  scored rung.

## Descoped / deferred

- **A programmatic contract check.** The ladder shows the protocol cannot see a
  persisted raw store; it does not add a guard that detects one. The signal is
  available — `survive_dir_bytes` per instance is already recorded, and a store
  that grows once per episode looks different from an artifact written once per
  batch — but a detector is a design question (thresholds, false positives on
  genuinely large artifacts) rather than ladder work. Pick it up when a SUT
  outside our control is measured through `--reset-at`; today every phased run is
  on a SUT we wrote.
- **Longer-schedule resolution.** Quarter-steps overlap at `n = 112`. Not chased:
  the brief's question was whether the band is wide enough to separate a partial
  rung *cleanly*, and against floor and ceiling it is. Documented as the limit.
- **`./run.sh ladder-phased` is not itself a CI step**, matching `./run.sh
  ladder`, which is not either. The claims are asserted by
  `tests/test_consolidating_memory_clbench.py`, which CI runs; the target is the
  human-readable rendering of the same runs.

## Observations

- **The venv was broken on entry** and `AGENTS.md`'s repair recipe does not fix
  it: `.venv/bin/python` pointed at `/opt/data/home/.local/share/uv/...`, a HOME
  that no longer exists in this image. `uv python install 3.13` reports success
  and changes nothing, because the dangling symlink is not what it heals.
  `ln -sf ~/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13
  .venv/bin/python` is what worked; the site-packages tree was intact.
- `SubprocessSystem` has no `env` parameter — the SUT inherits the harness
  environment (`harness/sut_process.spawn_sut`), so knob-driven rungs are set
  with `monkeypatch.setenv` in tests and `env VAR=value` in `run.sh`.
- `tests/test_docs_links.py` reads tracked files, so a link to a doc you have
  written but not yet committed fails in a way that looks like a broken link.
  Commit the new file first, then run it.
- The whole ladder runs in about ten seconds. The brief budgeted a day, on the
  assumption that a keyless ladder is cheap; it was cheaper than that.

## Follow-ups

### Considered and dropped

- Renaming `associative_memory` to advertise its contract-violating role under
  the phased protocol. It is the uniform ladder's full-retention ceiling and that
  name is correct there; the phased ladder names its *rung* `raw-store-control`,
  which puts the label where the role is.
