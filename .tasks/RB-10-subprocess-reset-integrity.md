# RB-10 Subprocess RESET integrity: process-group kill, timeout-kill, readline

**Priority:** high
**Blocked by:** nothing
**Depends-on (external):** none
**Touches:** `harness/sut_process.py` (`kill_sut`, `spawn_sut`, `_readline_with_timeout`),
`retention_bench/system.py` (`SubprocessSystem._exchange`), `docs/sut-interface.md`, `tests/`

## Context

The 2026-07-07 v0.1 review (`docs/reviews/2026-07-07-v0.1-review.md`, findings 1–3) found
that the harness's headline mechanism — the hard RESET, "SIGKILL + only disk survives" — is
weaker than the docs claim for exactly the SUT class the benchmark targets (multi-process
agent scaffolds). Verified against the code 2026-07-08:

- **`kill_sut` (`harness/sut_process.py:313`) SIGKILLs only the direct child.** No
  `start_new_session=True` at spawn, no `killpg` anywhere. `docs/sut-interface.md` says
  children "MUST be killable by SIGKILL to the parent's process group," but the harness
  never creates or signals a process group — so a spawned helper (e.g. a socket server the
  respawned SUT reconnects to) can keep in-memory state alive **across the discontinuity**.
  That is a hole in the benchmark's core semantic. Container mode already enforces this via
  `docker rm -f`.
- **Timeout doesn't kill.** `docs/sut-interface.md:147` says timeout SIGKILLs the SUT, but
  `SubprocessSystem._exchange` (`retention_bench/system.py:352`) only raises; the wedged
  process lives until `shutdown()`/GC.
- **`_readline_with_timeout` (`sut_process.py:280`) has two buffering edges:** it `select()`s
  the raw fd then calls buffered `readline()` — (a) a reply written in chunks without a
  trailing newline blocks past the timeout; (b) two lines emitted at once leave the second in
  Python's TextIO buffer, so the next `select()` can spuriously time out with a complete
  reply already buffered. These failure modes land on *misbehaving* SUTs, where clear errors
  matter most.

## Goal

Make the subprocess RESET guarantee mechanical, not trust-based: a RESET provably kills the
whole process tree, a timeout actually kills, and the line protocol can't spuriously time out
or block. Align the docs to what's enforced.

## Acceptance criteria

- [ ] `spawn_sut` starts the SUT in its own session/process group (`start_new_session=True`),
      and `kill_sut` signals the **group** (`killpg`), so children die with the parent.
- [ ] On timeout, `_exchange` SIGKILLs the SUT (via the same group kill) before/along with
      raising `SUTTimeout` — no wedged survivor.
- [ ] `_readline_with_timeout` uses a non-blocking fd with an explicit line buffer (or a
      reader thread) so partial writes time out cleanly and buffered second lines aren't lost.
- [ ] `docs/sut-interface.md` updated: subprocess mode now enforces process-group kill;
      state the container path is the independently-enforced one; timeout behaviour matches
      code.
- [ ] **Tests** (all currently absent): a SUT that spawns a child (assert the child is dead
      after RESET), the `SUTTimeout` path, and a mid-run SUT crash surface as clear errors.

## Decisions already made

- **`setsid` + `killpg` for subprocess**, not a per-child bookkeeping scheme — it's the
  ~5-line mechanical fix and matches container mode's whole-tree semantics. (Review 2026-07-07.)

## Out of scope

- Container-mode kill (already correct via `docker rm -f`).
- The `--stderr-log` ergonomics fix (RB-13) — related file, different concern.
