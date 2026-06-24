# Debrief: RB-6 Reference-ladder figure + SUT-list update

**Completed:** 2026-06-24
**Commit:** 82e7a51

## What shipped

The pre-C17 validity artifact, keyless and offline:

- **`./run.sh ladder`** — a new subcommand (mirrors `smoke`) that sweeps the
  three keyless reference SUTs (`no_state` → `bounded_memory` →
  `associative_memory`) over the reset axis on `symbolic_associative_retention`,
  printing labelled curves. `run.sh` is on `PUBLIC_PATHS`, so it ships.
- **`docs/reference-ladder.md`** — committed P/C/R(k) + normalised-retention table
  for all three rungs, two ASCII bar readings (raw `R(k)` and normalised), and the
  interpretation. `docs/` is public.
- **README** — broadened the reference-SUT description to name the full ladder and
  added a "reference ladder" pointer block + `./run.sh ladder`.

Numbers (deterministic, from `./run.sh ladder`):

| SUT | P | C | R(k) | norm |
|---|---:|---:|---:|---:|
| `no_state` | 0.000 | 0.615 | 0.000 | 0.000 |
| `bounded_memory` | 0.000 | 0.462 | 0.462 | 1.000 |
| `associative_memory` | 0.000 | 0.615 | 0.615 | 1.000 |

Full suite: 75 passed, 2 skipped. `scripts/promote.sh dryrun` clean.

## Descoped / deferred

- **No matplotlib PNG.** matplotlib is not in the venv, and a binary that needs a
  plotting dep to regenerate would undercut the "reproducible with no extra deps /
  no API key" credibility story. Committed numeric table + ASCII bars + a public
  one-command regenerator (`./run.sh ladder`) satisfy the brief's "figure **and/or**
  numeric table" criterion. A PNG can be added later if a writeup needs it.
- **No `scripts/` regen script** — `scripts/` is dev-only (not on `PUBLIC_PATHS`),
  so a script there wouldn't reach the public release. Put the regenerator in
  `run.sh` (public) instead.

## Design decisions

- **Regenerator lives in `run.sh`, not `scripts/`** — public-path reasons above;
  also discoverable next to `smoke`.
- **Plot raw `R(k)` *and* normalised retention, with explicit honest framing**
  rather than implying a graded normalised ladder. The data forced this (see
  Observations): on the headline normalised metric `bounded_memory` reads 1.0, so
  a naive "three graded rungs" claim would be false. The doc states plainly that
  `bounded_memory` is capacity-limited, not reset-lossy.
- **Excluded `notes_llm` / `constructive` from the figure** (pre-decided in brief)
  to keep it keyless/offline.

## Observations

- **The headline metric separates floor-vs-retainers, not a graded retention
  ladder, on this task.** Because `symbolic_associative_retention` trains all
  facts before probing, `bounded_memory`'s FIFO cap evicts at the *ceiling* too —
  so its cap lowers `C` (0.462 vs 0.615) but everything it can hold survives every
  hard reset, giving normalised retention 1.0. The capacity tier shows up only in
  raw `R(k)`. This is genuinely a *better* validity story (normalised retention
  isolates retention fidelity from capacity), but it is not the "graded middle
  rung on the normalised axis" the ladder framing might have implied. Worth
  carrying into any C17 public narrative.
- `R(k)` is reset-count-insensitive here (identical at k=12 and k=25) — these
  mechanisms either fully persist or fully lose, so the number of resets doesn't
  matter; mechanism does.

## Follow-ups

### Filed as tasks

- None filed yet — the reset-lossy SUT below is left for Toby to triage (it is the
  natural next reference SUT and informs how the C17 narrative should read).

### Considered and dropped

- A matplotlib PNG now — dropped for the reproducibility reason above; revisit at
  writeup time, not as benchmark infra.

### Candidate (surfaced, not yet filed)

- **Reset-lossy reference SUT** — persists to the survive-dir but drops a fraction
  of state per reset (e.g. probabilistic corruption), populating a middle point on
  the *normalised* axis (0 < norm < 1), distinct from `bounded_memory`'s capacity
  limit. This is the rung that would make the normalised metric itself look graded.
  Flagged in `docs/reference-ladder.md` ("Not yet on the ladder").
