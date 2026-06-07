# C10 Frozen corpus for the concept-drift reset schedule

**Priority:** medium
**Blocked by:** nothing
**Touches:** `retention_bench/`, `suts/constructive/`, `tests/`

## Context

C3 and C4 both ran on the seed-driven `blind_spectrum_monitoring` variant
`five_ch_wide` (13 latent channels, no on-disk corpus needed). The richer story
the pivot wants — placing hard resets *on* vs *just off* a concept-drift boundary
to expose a non-monotonic retention curve (a reset that lands on drift can *help*
by clearing stale belief; C1's nuance) — needs the task's `default` 3-stage
schedule, whose `corpus_id: mixed_grid_lifecycle` requires a frozen corpus on
disk. The task raises `FileNotFoundError` without it (noted in
`.tasks/debriefs/C3.md`). The C4 driver (`retention_bench.gain_curve`) already
accepts arbitrary schedules including `ExplicitBoundaries`, so this is a *data*
prerequisite, not a code gap.

## Goal

Generate / locate the `mixed_grid_lifecycle` frozen corpus so the `default`
drift schedule runs, then drive an `ExplicitBoundaries` sweep that places resets
on and off the stage boundaries and renders the resulting gain-vs-`k` curve.

## Acceptance criteria

- [ ] The `default` (3-stage) `blind_spectrum_monitoring` schedule runs end-to-end
      through `SubprocessSystem` without `FileNotFoundError` (corpus present /
      generated reproducibly).
- [ ] An `ExplicitBoundaries` sweep placing resets on-vs-off drift boundaries
      runs via `retention_bench.gain_curve` and produces a curve.
- [ ] Corpus generation is documented (how it's produced / where it lives) so a
      fresh dev container can reproduce it; relevant tests pass.

## Relevant files

- `/home/agent/src/cl-bench/src/tasks/blind_spectrum_monitoring/` (corpus loader,
  `corpus_id`, `clbench setup`-style generation)
- `retention_bench/gain_curve.py`, `retention_bench/reset_schedule.py`
  (`ExplicitBoundaries`)
- `tests/test_constructive_clbench.py`, `tests/test_gain_curve.py`

## Decisions already made

- `ExplicitBoundaries` (C2) is the tool for placing resets on/off stage boundaries
  (`reset_schedule.py` docstring). Keyed by 1-based completed-instance ordinal.
- A retaining-but-imperfect SUT (or the constructive SUT once it produces non-junk
  reward) is what makes the curve *shaped*; with the gibberish SUT the band stays
  excluded. C10 is about the corpus + drift placement, not SUT reward quality.

## Out of scope

SUT reward quality / making the constructive SUT non-gibberish. AURC / summary
statistics over the curve.
