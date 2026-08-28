# RB-24 Naive-SGD contrast arm at extreme k

**Priority:** high
**Blocked by:** nothing
**Depends-on (external):** constructive-retention CR-30 (`--mode naive-sgd-hop2`)
**Touches:** `runs/`, `TASKS.md`, `.tasks/debriefs/`

## Context

RB-15 measured the constructed hop-2 SUT through real process-kill RESETs on
2026-07-29 and found retention flat at ceiling (`R(k) = 0.6154`, norm_gain 1.000)
across k = 3, 6, 12 with zero seed spread, dropping to `R = P` exactly below a
threshold reset spacing.

The RB-15 sweep design named a naive-SGD contrast arm as a required control, with
this reasoning:

> A contrast arm on the same task (CR's naive-SGD baseline, Δret ≈ −0.98 on this
> increment) at the extreme `k` values. Without it a flat line is unfalsifiable —
> nothing distinguishes "flat because constructed" from "flat because the harness
> isn't resetting what we think".

That arm was not run. A `no_state` control was run instead and reached `R(k) = 0.000`
under resets, which establishes the harness genuinely resets — the *second* half of
the rationale. The first half is still open: nothing yet contrasts constructed
flatness against SGD degradation **on the same increment, through the same harness**.

This is the cheapest thing that makes the RB-15 flat line falsifiable, and it is the
kind of gap a reader finds before we do.

## Goal

Run `--mode naive-sgd-hop2` through the RB-15 sweep at the extreme reset points and
report `R(k)` alongside the constructed arm, so the flat line has a control that could
have come out otherwise.

## Acceptance criteria

- [ ] Naive-SGD arm run at the extreme k values (at minimum `--reset-every 64` (k=3)
      and `--reset-every 16` (k=12) — the region where the constructed arm fires).
- [ ] 3 seeds, matching RB-15; escalate only if spread appears.
- [ ] Raw `R(k)` reported as primary, normalised gain secondary — same convention as
      RB-15, for the same structural-CI reason.
- [ ] Result stated as a contrast against the constructed arm's `0.6154 / 1.000`, with
      an explicit sentence on whether the flat line survives the control.
- [ ] `CONSTRUCTIVE_HOP2_BASE_CACHE` set (uncached ≈ 28 min/arm, cached ≈ 3.5 min).
- [ ] Notebook entry in `constructive-retention/notebook/experiments/` updated or
      added, and RB-15's entry cross-linked so the omission is visible in the record.
- [ ] Logs under `runs/RB-24-<date>/` with the `sweep.sh` used.

## Relevant files

- `.tasks/debriefs/RB-15-m2-constructed-mode-gain-curve.md` — what ran, what didn't
- `constructive-retention/notebook/experiments/RB-15-constructed-hop2-reset-sweep.md`
- `constructive-retention/constructive_retention/baselines.py` — `NaiveSGDContinue`
- `runs/RB-15-2026-07-29/sweep.sh` — the sweep to mirror
- `AGENTS.md` (both repos) — cross-repo rules, base-cache env var

## Decisions already made

- **Extreme k only, not the full sweep.** The question is whether an SGD arm degrades
  where the constructed arm is flat. The mid-range points add cost without adding
  discriminating power.
- **3 seeds.** RB-15's spread was exactly zero at every point; matching it keeps the
  comparison honest and cheap. Escalate only on observed spread.
- **The expected result is degradation** (CR reports Δret ≈ −0.98 on this increment
  in-process). A *non*-degrading SGD arm would be the interesting outcome and would
  put the constructed arm's claim in question — which is exactly why this is worth
  running rather than assuming.

## Out of scope

- Re-running the constructed arm. RB-15's numbers stand.
- Claiming Milestone 2. M2 needs non-overlapping CIs and the normalised-gain interval
  is structurally wide; that is a separate problem.
- The `RebalancedSGDOracle` ceiling arm. Useful eventually, not needed to falsify a
  flat line.
- Removing the acquisition window (per-instance construction) — CR-side algorithm work.
