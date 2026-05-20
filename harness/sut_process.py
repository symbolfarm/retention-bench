"""SUT subprocess wrapper.

I/O channel is stdin/stdout with JSON Lines framing, per docs/sut-interface.md:

  Harness -> SUT (one line):
    {"event_id":"evt-0001","event_type":"QUIZ","stage_input":"..."}

  SUT -> Harness (one line):
    {"event_id":"evt-0001","answers":[{"id":"q1","text":"..."}]}   # for QUIZ
    {"event_id":"evt-0001","stage_output":""}                       # for READ

The SUT's working directory is DIR. The SUT may read/write freely there;
the harness reserves the `.harness/` prefix for itself.

RESET = SIGKILL + wait; the SUT is not given a chance to flush.
Per-event timeout default 300s (5 min); see docs/task-definition-schema.md.
"""

from __future__ import annotations

import json
import os
import select
import shlex
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class SUTError(RuntimeError):
    """SUT failed in a way that should abort the run."""


class SUTTimeout(SUTError):
    """SUT did not respond within the per-event timeout."""


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
    extra_pythonpath: Optional[list[Path]] = None,
) -> SUTHandle:
    """Spawn a SUT subprocess. cwd = DIR. stdin/stdout = pipes.

    `extra_pythonpath` is prepended to PYTHONPATH so that `python -m <module>`
    entrypoints in SUT manifests resolve correctly when cwd=DIR.
    """
    stderr_fh = open(stderr_log, "ab") if stderr_log else subprocess.DEVNULL
    env = os.environ.copy()
    # Make DIR discoverable both via cwd and explicitly via env.
    env["RETENTION_BENCH_DIR"] = str(dir_path)
    # Since cwd=DIR, the SUT loses access to packages importable from the
    # caller's cwd. Propagate the harness repo root + the SUT package dir
    # (if --sut was used) onto PYTHONPATH so that `python -m no_state` and
    # `python -m harness.stubs.echo_sut` both resolve.
    repo_root = str(Path(__file__).resolve().parent.parent)
    extra = [str(p) for p in (extra_pythonpath or [])]
    existing_pp = env.get("PYTHONPATH", "")
    parts = [*extra, repo_root]
    if existing_pp:
        parts.append(existing_pp)
    env["PYTHONPATH"] = os.pathsep.join(parts)
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


def send_event(
    handle: SUTHandle,
    event_id: str,
    event_type: str,
    stage_input: str,
    timeout_s: float = 300.0,
) -> dict[str, Any]:
    """Send a single JSONL event to the SUT and read its single-line JSON reply.

    Returns the parsed reply dict. Shape (per docs/sut-interface.md):
      - QUIZ reply: {"event_id":..., "answers":[{"id":..., "text":...}, ...], ...}
      - READ reply: {"event_id":..., "stage_output":"", ...}

    Raises SUTTimeout if no reply arrives within timeout_s; SUTError on protocol
    violations (closed stdout, bad JSON, wrong event_id, wrong shape).
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
    reply = _readline_with_timeout(handle.process.stdout, timeout_s)
    if reply is None:
        raise SUTTimeout(
            f"SUT did not respond to {event_id} within {timeout_s:.0f}s"
        )
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
    if event_type == "QUIZ":
        if "answers" not in parsed:
            raise SUTError(
                f"SUT QUIZ reply for {event_id} missing 'answers' list: {parsed!r}"
            )
        if not isinstance(parsed["answers"], list):
            raise SUTError(
                f"SUT QUIZ reply 'answers' for {event_id} must be a list: {parsed!r}"
            )
    # READ replies are not strictly required to carry stage_output; accept absence.
    return parsed


def _readline_with_timeout(stream, timeout_s: float) -> Optional[str]:
    """Read a single line from `stream` with a wall-clock timeout.

    Returns the line (including trailing newline), '' on EOF, or None on timeout.
    Uses select() on the underlying fd; works on POSIX. Windows is out of scope.
    """
    fd = stream.fileno()
    ready, _, _ = select.select([fd], [], [], timeout_s)
    if not ready:
        return None
    return stream.readline()


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
