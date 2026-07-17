"""RB-10: the hard-RESET kill and line protocol are mechanical, not trust-based.

These exercise ``harness.sut_process`` directly (no cl-benchmark needed):

  * ``kill_sut`` SIGKILLs the SUT's whole *process group*, so a child the SUT
    spawned dies with it — the hole finding 1 of the 2026-07-07 review flagged
    (a survivor could carry in-memory state across the RESET discontinuity); and
  * ``_readline_with_timeout`` reads the raw fd with an explicit line buffer, so
    a partial write (no trailing newline) times out cleanly instead of blocking,
    and a second line emitted at once is returned rather than spuriously timing
    out (finding 3).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from harness import sut_process

# A SUT that, on startup, spawns a long-lived grandchild (a plain child process,
# NOT in a new session) and records both pids to the survive-dir. A naive
# single-pid kill of the SUT would leave the grandchild running; a process-group
# kill takes it out. It then echoes a reply per stdin line so the test can
# confirm the child exists before killing.
_CHILD_SPAWN_SUT = r"""
import json, os, subprocess, sys
from pathlib import Path

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
Path("pids.json").write_text(json.dumps({"parent": os.getpid(), "child": child.pid}))
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    json.loads(line)
    sys.stdout.write(json.dumps({"action": {"ok": True}}) + "\n")
    sys.stdout.flush()
"""


def _proc_state(pid: int):
    """Return the /proc state char for `pid` ('R','S','Z',…) or None if gone.

    A killed process may momentarily be a zombie ('Z') before its (now-reparented)
    slot is reaped; both 'Z' and gone mean 'no longer running'.
    """
    try:
        with open(f"/proc/{pid}/stat") as fh:
            data = fh.read()
    except (FileNotFoundError, ProcessLookupError):
        return None
    # comm (field 2) is parenthesised and may contain spaces — split after the ')'.
    return data[data.rindex(")") + 2]


def _wait_dead(pid: int, timeout_s: float = 3.0) -> str | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = _proc_state(pid)
        if state in (None, "Z"):
            return state
        time.sleep(0.02)
    return _proc_state(pid)


def test_reset_kills_whole_process_group(tmp_path):
    sut_file = tmp_path / "child_spawn_sut.py"
    sut_file.write_text(_CHILD_SPAWN_SUT)

    handle = sut_process.spawn_sut(
        [sys.executable, str(sut_file)], dir_path=tmp_path, invocation_index=0
    )
    try:
        # Drive one round-trip so we know the child was spawned + pids written.
        handle.process.stdin.write(json.dumps({"prompt": "x"}) + "\n")
        handle.process.stdin.flush()
        reply = sut_process._readline_with_timeout(handle.process.stdout, 10.0)
        assert reply is not None and reply.strip(), "SUT did not reply"

        pids = json.loads((tmp_path / "pids.json").read_text())
        child_pid = pids["child"]
        # The grandchild is alive right now (running/sleeping, not a zombie).
        assert _proc_state(child_pid) in ("R", "S", "D")

        sut_process.kill_sut(handle)

        # The RESET killpg must have taken the grandchild too.
        assert _wait_dead(child_pid) in (None, "Z"), "child survived the process-group kill"
        # ...and the SUT itself is reaped.
        assert handle.process.poll() is not None
    finally:
        # Belt-and-braces cleanup if an assertion failed mid-way.
        try:
            os.killpg(handle.process.pid, 9)
        except (ProcessLookupError, PermissionError):
            pass


# --------------------------------------------------------------------------- #
# _readline_with_timeout buffering edges (finding 3).
# --------------------------------------------------------------------------- #
def _pipe_reader():
    """A (read_stream, write_fd) pair mimicking a SUT's stdout wired to a pipe.

    read_stream is a text-mode file object like proc.stdout; write_fd is the raw
    fd we push bytes into to simulate SUT writes.
    """
    r, w = os.pipe()
    read_stream = os.fdopen(r, "r", buffering=1, encoding="utf-8")
    return read_stream, w


def test_readline_times_out_cleanly_on_partial_write(tmp_path):
    read_stream, w = _pipe_reader()
    try:
        # Write a chunk with NO trailing newline: the old select()+readline()
        # would block in readline() past the timeout; the fix must return None.
        os.write(w, b'{"partial":')
        t0 = time.monotonic()
        result = sut_process._readline_with_timeout(read_stream, 0.3)
        elapsed = time.monotonic() - t0
        assert result is None
        assert elapsed < 2.0, f"blocked past the timeout ({elapsed:.2f}s)"

        # The partial bytes are retained: completing the line returns the whole line.
        os.write(w, b' 1}\n')
        result2 = sut_process._readline_with_timeout(read_stream, 1.0)
        assert result2 == '{"partial": 1}\n'
        assert json.loads(result2) == {"partial": 1}
    finally:
        os.close(w)
        read_stream.close()


def test_readline_returns_buffered_second_line_without_reblocking(tmp_path):
    read_stream, w = _pipe_reader()
    try:
        # Two complete lines emitted at once. The old code pulled both into the
        # TextIO buffer on the first readline(), so the next select() could time
        # out with line two already buffered. The fix must return each in turn.
        os.write(w, b'{"a":1}\n{"b":2}\n')
        first = sut_process._readline_with_timeout(read_stream, 1.0)
        assert first == '{"a":1}\n'
        # Second call: no more bytes on the fd, but line two is buffered — must
        # return immediately, NOT time out.
        t0 = time.monotonic()
        second = sut_process._readline_with_timeout(read_stream, 5.0)
        assert second == '{"b":2}\n'
        assert time.monotonic() - t0 < 1.0, "re-selected instead of using the buffer"
    finally:
        os.close(w)
        read_stream.close()


def test_readline_reports_eof_as_empty_string(tmp_path):
    read_stream, w = _pipe_reader()
    try:
        os.close(w)  # writer closes → EOF on the read side
        assert sut_process._readline_with_timeout(read_stream, 1.0) == ""
    finally:
        read_stream.close()


def test_readline_surfaces_unterminated_remainder_at_eof(tmp_path):
    read_stream, w = _pipe_reader()
    try:
        os.write(w, b'{"no_newline":true}')
        os.close(w)  # EOF with buffered, unterminated content
        result = sut_process._readline_with_timeout(read_stream, 1.0)
        assert result == '{"no_newline":true}'
        # Next call after the remainder is drained is a clean EOF.
        assert sut_process._readline_with_timeout(read_stream, 1.0) == ""
    finally:
        read_stream.close()
