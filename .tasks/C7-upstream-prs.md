# C7 Upstream PRs — plugin entry-point discovery (+ optional reset schedule)

**Priority:** low
**Blocked by:** nothing
**Touches:** `unknown` (CL-Bench fork/PR, not this repo)

## Context

CL-Bench's registry discovers systems/tasks by internal filesystem scan only —
no entry-point/plugin hook — so an external package registers via a thin launcher
that imports-then-delegates (the C0/C2 approach works fine this way). A small
upstream PR adding entry-point discovery would let `retention_bench` register
cleanly. Optional second PR: a first-class per-boundary reset schedule (we do this
system-side today, so it's a convenience, not a need).

A third candidate surfaced by the first real CI run (2026-07-19, commit
`77ec477`): CL-Bench's `pyproject.toml` has no package-data config, so wheel
installs (`pip install cl-benchmark @ git+...`) silently drop the
`templates/`, `variants/`, and `schedules/` files its tasks load via
`Path(__file__).parent` — every task construction fails with
"Unknown variant ...". Only *editable* installs work. The fix is a few lines
(`[tool.setuptools] include-package-data` + a `package-data` glob, or
MANIFEST.in); arguably the most valuable of the three PRs since it breaks
every downstream pip consumer, not just plugin ergonomics. Until it lands,
our CI reinstalls the pin editable as the last pip step, and RB-14/C17
should document the editable-install requirement for end users.

Good-citizen PRs that also seed the relationship (coordinate with C5).

## Goal

One or two upstream PRs against `pgasawa/continual-learning-bench`.

## Acceptance criteria

- [ ] PR 1: entry-point plugin discovery in `registry.py`, backward compatible.
- [ ] (optional) PR 2: first-class reset schedule in the runner.
- [ ] PR 3: package-data config so wheel installs ship `templates/`,
      `variants/`, `schedules/` (see Context; unblocks non-editable installs
      for all downstream consumers).
- [ ] Coordinated with the authors (C5) before opening.

## Decisions already made

- Neither PR is a blocker for our work (C0 finding); these are upstreaming, not
  prerequisites.

## Out of scope

Our own package changes (C2).
