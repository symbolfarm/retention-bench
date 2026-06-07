# C4 Reset-axis (retention curve) reporting + gain reconciliation

**Priority:** medium
**Blocked by:** C3
**Touches:** `retention_bench/`

## Context

Our net-new reporting axis is retention as a function of the number of hard
resets `k` — CL-Bench's gain metric has no k-axis. The C0 spike showed our
metric reconciles with theirs: read their normalized gain
`(r_sf - r_sl)/(r_max - r_sl)` with `r_sf -> R(k)`, `r_sl -> P`, `r_max -> C`.
We contribute the axis, not a competing formula (see `docs/clbench-pivot-plan.md`).

## Goal

Given runs at several reset densities `k`, produce a retention curve (gain vs k)
and confirm it reduces to CL-Bench's gain at the appropriate `k`.

## Acceptance criteria

- [ ] A driver that runs the C2 system at a sweep of `k` values and collects
      per-instance rewards per `k`.
- [ ] Aggregation producing gain-vs-`k` (reuse the k-axis logic from
      `scorer/aggregate.py`); rendered as a table/curve.
- [ ] Documented reconciliation: at the matching `k`, our number equals
      CL-Bench's normalized gain on the same run.

## Relevant files

- `scorer/aggregate.py` (k-axis aggregation to port)
- `retention_bench/` (C2/C3)

## Out of scope

Outreach (C5); new task (C6); upstream PRs (C7).
