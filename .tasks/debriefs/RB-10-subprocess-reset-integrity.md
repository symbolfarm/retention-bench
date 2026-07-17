# Debrief: RB-10 Subprocess RESET integrity — process-group kill, timeout-kill, readline

**Completed:** 2026-07-17
**Commit:** e2bef7f

## What shipped

The subprocess hard-RESET guarantee is now mechanical rather than trust-based
(2026-07-07 v0.1 review, findings 1-3):

- **Process-group kill.** `spawn_sut` launches the SUT with
  `start_new_session=True` (subprocess *and* container Popen), so it leads its
  own process group with `pgid == pid`. `kill_sut` now `os.killpg`s that group
  (new `_killpg` helper, with a direct-pid fallback if setsid didn't take), so
  children the SUT spawned die with it — a surviving helper can no longer carry
  in-memory state across the discontinuity.
- **Kill-on-timeout / crash.** `SubprocessSystem._exchange` SIGKILLs the SUT's
  group before raising `SUTTimeout`, and also on the mid-run stdout-close crash
  path before raising `SUTError`. New `_kill_current_handle()` drops the handle
  so the next `respond()` respawns cleanly; it is deliberately *not* a scheduled
  reset (leaves `kills`/`scheduled_resets`/wipe and the weakref finalizer alone).
- **`_readline_with_timeout` rework.** Now drives the raw fd with `os.read`
  (only after `select` reports readable, so it never blocks) plus an explicit
  per-stream byte buffer kept in a module-level `WeakKeyDictionary`. Partial
  writes (no trailing newline) time out cleanly with bytes retained for a later
  call; a second line emitted at once is returned rather than spuriously timing
  out with a reply already sitting in a buffer. Unterminated remainder at EOF is
  surfaced as the final line.
- **Docs.** `docs/sut-interface.md` now states process-group kill is enforced
  (subprocess: `start_new_session`+`killpg`; container: `docker rm -f` as the
  independently-enforced path), tightens the "no unkillable children" rule to
  forbid detaching into a *new* session, and aligns the timeout/crash wording
  with the code.
- **Tests.** `tests/test_sut_reset_integrity.py` (harness-level, no cl-benchmark
  needed): child-spawned-process killed by RESET, plus the four readline edges.
  `tests/test_sut_timeout_and_crash.py` (SubprocessSystem-level, importorskip):
  timeout SIGKILLs the group, mid-run crash → clear `SUTError`.

Full suite: **93 passed, 2 skipped** (both docker-gated) on the 3.13 venv.

## Descoped / deferred

Followed the scope cap. Did not touch the related-but-separate concerns the
brief excluded: container-mode kill (already correct), `--stderr-log` ergonomics
(RB-13), `_split_reply` error taxonomy (RB-13), packaging/CI (RB-11). Left the
dead book-track `send_event` in place — it shares the improved
`_readline_with_timeout` and now benefits from it, but its removal is RB-13.

## Design decisions

- **Non-blocking-fd + explicit line buffer, not a reader thread.** The brief
  offered either. The fd approach is threadless (no lifecycle/cleanup, no
  join-on-kill), and the only real cost — carrying surplus bytes across calls —
  is handled by a `WeakKeyDictionary` keyed on the stream object (verified
  weak-referenceable), which self-clears when a killed SUT's stdout is GC'd so a
  respawn gets a fresh buffer. `os.read` is only issued after `select` reports
  readable, so it never blocks; no `O_NONBLOCK` fiddling needed.
- **`start_new_session=True` on the container Popen too**, not just subprocess.
  Harmless (the docker *client* gets its own group; the container is still torn
  down by `docker rm -f`) and keeps `_killpg(proc.pid)` valid for both modes.
- **Kill on the mid-run-crash path as well as timeout.** The brief mandated
  kill-on-timeout; I extended the same `_kill_current_handle()` to the
  stdout-closed branch because a crashed *parent* can leave orphaned children,
  and reaping the group is the consistent hygienic choice. Both drop the handle.
- **Child-death asserted via `/proc/<pid>/stat` state (accept `Z` or gone), not
  `os.kill(pid, 0)`.** A killpg'd grandchild reparents to a possibly-non-reaping
  init and can sit as a zombie, for which `os.kill(pid, 0)` still succeeds; the
  state-char check (with a short poll) distinguishes "killed" from "running".

## Observations

- The worktree was branched from the v0.1 release commit `5183639`, not from
  `dev` (`356ee51`) as the brief stated — so `TASKS.md`, `.tasks/`, and the
  review doc were absent. Reset the worktree branch to `dev` (no work had
  started) before beginning. Worth checking `git log` against `dev` when a
  worktree looks empty.
- `python -c` / `-m` puts cwd first on `sys.path`, so the editable install
  pointing at the main checkout is shadowed by the worktree when running from
  it; still prefixed test runs with `PYTHONPATH=$PWD` and verified
  `retention_bench.__file__` / `harness.__file__` resolve into the worktree.

## Follow-ups

### Considered and dropped

- Killing on the JSON-decode-error path in `_exchange` too — out of scope, and
  a decode error means the SUT *did* reply (it's alive and well-behaved enough
  to respawn on the next call); no orphan-child risk. Left alone.
