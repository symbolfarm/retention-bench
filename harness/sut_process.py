"""SUT subprocess wrapper.

I/O channel is stdin/stdout with JSON Lines framing, per the pre-locked
decision in the M2 brief:

  Harness -> SUT (one line):
    {"event_id":"evt-0001","event_type":"QUIZ","stage_input":"..."}

  SUT -> Harness (one line):
    {"event_id":"evt-0001","stage_output":"..."}

The SUT's working directory is DIR. The SUT may read/write freely there;
the harness reserves the `.harness/` prefix for itself.

RESET = SIGKILL + wait; the SUT is not given a chance to flush.
"""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class SUTError(RuntimeError):
    """SUT failed in a way that should abort the run."""


@dataclass
class SUTHandle:
    process: subprocess.Popen
    process_id: str  # stable harness-side ID like "sut-01"
    invocation_index: int  # 0-based count of spawns in this run

    @property
    def pid(self) -> int:
        return self.process.pid


def spawn_sut(
    command: list[str],
    dir_path: Path,
    invocation_index: int,
    stderr_log: Optional[Path] = None,
) -> SUTHandle:
    """Spawn a SUT subprocess. cwd = DIR. stdin/stdout = pipes."""
    stderr_fh = open(stderr_log, "ab") if stderr_log else subprocess.DEVNULL
    env = os.environ.copy()
    # Make DIR discoverable both via cwd and explicitly via env.
    env["RETENTION_BENCH_DIR"] = str(dir_path)
    # Since cwd=DIR, the SUT loses access to packages importable from the
    # caller's cwd. Propagate the harness repo root onto PYTHONPATH so that
    # `python -m harness.stubs.echo_sut` (and similar) still resolves.
    repo_root = str(Path(__file__).resolve().parent.parent)
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = repo_root + (os.pathsep + existing_pp if existing_pp else "")
    proc = subprocess.Popen(
        command,
        cwd=str(dir_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr_fh,
        env=env,
        text=True,
        bufsize=1,  # line-buffered
    )
    pid_str = f"sut-{invocation_index + 1:02d}"
    return SUTHandle(process=proc, process_id=pid_str, invocation_index=invocation_index)


def send_event(handle: SUTHandle, event_id: str, event_type: str, stage_input: str) -> str:
    """Send a single JSONL event to the SUT and read its single-line JSON reply.

    Returns the SUT's `stage_output` string.
    """
    msg = {"event_id": event_id, "event_type": event_type, "stage_input": stage_input}
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    try:
        assert handle.process.stdin is not None
        handle.process.stdin.write(line)
        handle.process.stdin.flush()
    except (BrokenPipeError, OSError) as e:
        raise SUTError(f"failed writing to SUT stdin for {event_id}: {e}") from e

    assert handle.process.stdout is not None
    reply = handle.process.stdout.readline()
    if not reply:
        rc = handle.process.poll()
        raise SUTError(
            f"SUT closed stdout before replying to {event_id} (exit={rc})"
        )
    try:
        parsed = json.loads(reply)
    except json.JSONDecodeError as e:
        raise SUTError(f"SUT reply for {event_id} not valid JSON: {e}: {reply!r}") from e
    if parsed.get("event_id") != event_id:
        raise SUTError(
            f"SUT reply event_id mismatch: sent {event_id!r}, got {parsed.get('event_id')!r}"
        )
    if "stage_output" not in parsed:
        raise SUTError(f"SUT reply for {event_id} missing 'stage_output': {parsed!r}")
    return str(parsed["stage_output"])


def kill_sut(handle: SUTHandle, timeout_s: float = 2.0) -> tuple[str, Optional[int]]:
    """Kill the SUT process. Returns (signal_name, exit_code).

    Per the brief: `RESET` is SIGKILL + wait, not graceful shutdown.
    """
    proc = handle.process
    # Close stdin first so a well-behaved SUT could exit on EOF; we don't wait.
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass

    sig_name = "SIGKILL"
    if proc.poll() is None:
        try:
            proc.send_signal(signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        exit_code = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        exit_code = None  # truly unresponsive; harness gives up waiting.
    return sig_name, exit_code


def shutdown_sut(handle: SUTHandle, timeout_s: float = 2.0) -> tuple[str, Optional[int]]:
    """Graceful shutdown at end of run: close stdin (EOF) and wait briefly,
    falling back to SIGKILL. Returns (signal_name, exit_code)."""
    proc = handle.process
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass
    try:
        exit_code = proc.wait(timeout=timeout_s)
        return "EOF", exit_code
    except subprocess.TimeoutExpired:
        return kill_sut(handle, timeout_s=timeout_s)


def parse_command(cmd: str | list[str]) -> list[str]:
    if isinstance(cmd, list):
        return list(cmd)
    return shlex.split(cmd)
