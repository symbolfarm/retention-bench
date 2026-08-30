# RB-25: Resolve the two survive-dir creation paths

**Status:** pending · **Priority:** low · **Blocked by:** none
**Touches:** `harness/dir_lifecycle.py`, `retention_bench/system.py`, `tests/`

## Why

`harness/dir_lifecycle.py` exposes `create_dir`, `snapshot_dir` and
`cleanup_dir`, and **no non-test code calls any of them** — `SubprocessSystem`
uses only `HARNESS_RESERVED_PREFIX` and `account_dir`. A real run creates its
survive-dir at `system.py:143-148`, and the wipe that defines the stateless prior
arm is `system.py:_wipe_survive_dir`, not in `dir_lifecycle` at all.

**This is not simply dead code, which is why it is a question and not a cleanup
order.** `system.py:145-147` carries a comment saying it deliberately matches
`dir_lifecycle.create_dir`, and `tests/test_subprocess_system.py:291` asserts the
two creation paths do not drift on what is excluded from
`account_dir`/`snapshot_dir`. So the module is currently acting as a reference
implementation that a test pins the live path against. Deleting it naively would
remove the thing the drift test compares to.

Surfaced 2026-08-30 while preparing the comprehension pass; noticed because a
card aimed at `dir_lifecycle` found the subject was somewhere else.

## What to decide

One of:

1. **Make it live** — have `SubprocessSystem` call `create_dir` so there is one
   path and the drift test becomes unnecessary.
2. **Make it explicitly a spec** — keep it, document it as the reference the live
   path is tested against, and say so in the module docstring so the next reader
   does not file this task again.
3. **Remove it** — delete the three unused functions and re-express the drift
   test as a direct assertion about the live path.

## Acceptance criteria

1. Exactly one of the above is implemented, with the reason recorded.
2. No behaviour change to a real run; the prior/stateless arm still wipes
   identically.
3. The full test suite passes, and the drift protection still exists in some form
   or its removal is justified.

## Notes

Residue of the retired book-track harness. Low priority: this is comprehension
debt, not a defect — nothing is currently wrong, it is just hard to read.
