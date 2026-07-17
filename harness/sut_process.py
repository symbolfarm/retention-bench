"""SUT subprocess wrapper.

This module owns the *process lifecycle* (spawn/kill/timeout-safe readline) —
launch primitives that are wire-format-agnostic. The live one-JSON-line-each-way
framing consumed by :class:`retention_bench.system.SubprocessSystem` is defined
there (``_exchange``), not here; this module's own framing helper for the
retired book-track ``READ``/``QUIZ`` event loop (``send_event``) was removed
with that harness (see docs/reviews/2026-07-07-v0.1-review.md, "Book-track
residue") and now lives only as a test helper in ``tests/test_docker_launch.py``.

The SUT's working directory is DIR. The SUT may read/write freely there;
the harness reserves the `.harness/` prefix for itself.

RESET = SIGKILL + wait; the SUT is not given a chance to flush. The SUT is
launched in its own session/process group (``start_new_session=True``) and the
kill signals the whole **group** (``killpg``), so children the SUT spawned die
with it — nothing survives a RESET except the on-disk survive-dir. (Container
mode enforces the same whole-tree semantics independently via ``docker rm -f``.)
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
import time
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


class SUTError(RuntimeError):
    """SUT failed in a way that should abort the run."""


class SUTTimeout(SUTError):
    """SUT did not respond within the per-event timeout."""


@dataclass
class ContainerSpec:
    """Everything spawn_sut needs to launch a SUT via `docker run` instead of
    a bare subprocess. Built by the harness from the SUT manifest's `image`
    and `env` fields (see docs/sut-interface.md).

    `dir_host_path` is the *host-daemon-visible* path to DIR (already
    translated for the DooD case via host_path_for_mount); it is bind-mounted
    at `DIR_CONTAINER_PATH` inside the container. `env_names` are forwarded
    by name (`-e NAME`), so values pass through from the harness environment
    to the container without ever being logged. `shim_host_path`, when set,
    bind-mounts the fake-openai test shim read-only and puts it on
    PYTHONPATH (the option-B test path; see B4a brief)."""
    image: str
    container_name: str
    dir_host_path: str
    env_names: list[str] = field(default_factory=list)
    shim_host_path: Optional[str] = None


# Fixed in-container mount point for DIR. The SUT sees DIR here regardless of
# where it lives on the host; RETENTION_BENCH_DIR and the workdir both point
# at it, matching the subprocess contract (cwd=DIR).
DIR_CONTAINER_PATH = "/dir"
SHIM_CONTAINER_PATH = "/shim"


@dataclass
class SUTHandle:
    process: subprocess.Popen
    process_id: str  # stable harness-side ID like "sut-01"
    invocation_index: int  # 0-based count of spawns in this run
    # When launched via docker, the `--name` of the container. kill/shutdown
    # use this to `docker rm -f` the container itself — killing the `docker
    # run` client process alone does NOT reliably stop the container.
    container_name: Optional[str] = None

    @property
    def pid(self) -> int:
        return self.process.pid


def host_path_for_mount(path: Path, repo_root: Path) -> str:
    """Translate a harness-visible path to the path the docker *daemon* sees.

    In the DooD case (dev container mounts the host's docker.sock), the daemon
    runs on the host, so `docker run -v <path>` must use the *host's* view of
    `path`, not the dev container's. We map the dev-container repo root to the
    host repo root via $HOST_WORKSPACE: a path under `repo_root` becomes
    `$HOST_WORKSPACE/<relative>`.

    If HOST_WORKSPACE is unset (bare-host case — the harness and daemon share a
    filesystem), the path is returned unchanged. If HOST_WORKSPACE is set but
    `path` is not under `repo_root`, we cannot translate it safely, so we raise
    rather than silently bind-mount a path the daemon can't resolve.
    """
    host_ws = os.environ.get("HOST_WORKSPACE")
    if not host_ws:
        return str(path)
    path = path.resolve()
    repo_root = repo_root.resolve()
    try:
        rel = path.relative_to(repo_root)
    except ValueError as e:
        raise SUTError(
            f"HOST_WORKSPACE is set ({host_ws!r}) but {path} is not under the "
            f"repo root {repo_root}; cannot translate the bind-mount path for "
            f"the docker daemon. Keep the runs dir under the repo, or unset "
            f"HOST_WORKSPACE when running on a bare host."
        ) from e
    return str(Path(host_ws) / rel)


def build_docker_argv(spec: ContainerSpec, entrypoint: list[str]) -> list[str]:
    """Build the `docker run` argv that launches a SUT over piped stdin/stdout.

    `-i` keeps stdin open (no `-t`: not a TTY, we pipe JSONL). `--rm` cleans up
    on exit; we also `docker rm -f` by name on RESET as a belt-and-braces stop.
    Env vars are forwarded by name only (`-e NAME`), so secret values never
    appear in argv or logs.
    """
    argv = [
        "docker", "run", "-i", "--rm",
        "--name", spec.container_name,
        "-v", f"{spec.dir_host_path}:{DIR_CONTAINER_PATH}",
        "-w", DIR_CONTAINER_PATH,
        "-e", f"RETENTION_BENCH_DIR={DIR_CONTAINER_PATH}",
    ]
    for name in spec.env_names:
        argv += ["-e", name]  # value forwarded from the daemon-launching env
    if spec.shim_host_path is not None:
        argv += [
            "-v", f"{spec.shim_host_path}:{SHIM_CONTAINER_PATH}:ro",
            "-e", f"PYTHONPATH={SHIM_CONTAINER_PATH}",
        ]
    argv.append(spec.image)
    argv += entrypoint
    return argv


def spawn_sut(
    command: list[str],
    dir_path: Path,
    invocation_index: int,
    stderr_log: Optional[Path] = None,
    extra_pythonpath: Optional[list[Path]] = None,
    container: Optional[ContainerSpec] = None,
) -> SUTHandle:
    """Spawn a SUT. stdin/stdout = pipes, JSONL framing.

    Two launch modes:
      - **subprocess** (default): run `command` directly with cwd=DIR. The host
        environment is inherited and `extra_pythonpath` is prepended to
        PYTHONPATH so `python -m <module>` entrypoints resolve from cwd=DIR.
      - **container** (`container` given): `command` is the in-container
        entrypoint argv; the harness wraps it in `docker run` (see
        build_docker_argv). DIR is bind-mounted, env forwarded by name, and the
        SUT package is expected to be installed in the image — so the host
        PYTHONPATH logic does not apply.
    """
    stderr_fh = open(stderr_log, "ab") if stderr_log else subprocess.DEVNULL

    if container is not None:
        docker_argv = build_docker_argv(container, command)
        # The docker *client* inherits the harness env so `-e NAME` passthrough
        # can read each value; only the named vars actually cross into the
        # container. cwd is irrelevant for the client (workdir is set via -w).
        proc = subprocess.Popen(
            docker_argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_fh,
            env=os.environ.copy(),
            text=True,
            bufsize=1,
            start_new_session=True,  # own process group; killpg on RESET
        )
        pid_str = f"sut-{invocation_index + 1:02d}"
        return SUTHandle(
            process=proc,
            process_id=pid_str,
            invocation_index=invocation_index,
            container_name=container.container_name,
        )

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
    # The manifest `entrypoint` (e.g. ["python", "-m", "no_state"]) names the
    # *container* interpreter. In subprocess mode we run on the host, where a
    # bare `python` may not exist (only `python3`) and, more importantly, only
    # the harness's own interpreter is guaranteed to have the SUT's deps
    # installed (e.g. the active venv). Launch python-module SUTs under
    # sys.executable — the same choice the built-in stub launch makes
    # (harness/__main__.py). Non-python entrypoints are left untouched.
    launch = list(command)
    if launch and os.path.basename(launch[0]) in ("python", "python3"):
        launch[0] = sys.executable
    proc = subprocess.Popen(
        launch,
        cwd=str(dir_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr_fh,
        env=env,
        text=True,
        bufsize=1,  # line-buffered
        # Own session/process group so a RESET's killpg takes the SUT's whole
        # child tree with it (agent-scaffold SUTs spawn helpers); pgid == pid.
        start_new_session=True,
    )
    pid_str = f"sut-{invocation_index + 1:02d}"
    return SUTHandle(process=proc, process_id=pid_str, invocation_index=invocation_index)


# Per-stream leftover bytes carried across _readline_with_timeout calls. Keyed
# weakly by the stream object, so it clears itself when a killed SUT's stdout is
# collected and a respawn gets a fresh (empty) buffer.
_line_buffers: "weakref.WeakKeyDictionary[Any, bytearray]" = weakref.WeakKeyDictionary()


def _readline_with_timeout(stream, timeout_s: float) -> Optional[str]:
    """Read a single newline-terminated line from `stream` within a wall-clock
    timeout, driving the raw fd directly with an explicit byte buffer.

    Returns the line (including trailing newline), '' on EOF, or None on timeout.
    POSIX only; Windows is out of scope.

    Why not ``select()`` + buffered ``readline()``: that combination has two
    failure modes on misbehaving SUTs — (a) a reply dribbled out in chunks with
    no trailing newline blocks in ``readline()`` *past* the timeout, and (b) two
    lines emitted at once get pulled into Python's TextIO buffer together, so the
    next ``select()`` spuriously times out with a complete reply already buffered.
    Reading the fd ourselves and keeping the surplus in ``_line_buffers`` fixes
    both: partial writes time out cleanly (bytes stay buffered for a later call),
    and a buffered second line is returned without re-selecting. We only
    ``os.read`` after ``select`` reports readable, so the read never blocks.
    """
    buf = _line_buffers.get(stream)
    if buf is None:
        buf = bytearray()
        _line_buffers[stream] = buf

    # A complete line may already be buffered from a previous read.
    nl = buf.find(b"\n")
    if nl != -1:
        return _pop_line(buf, nl)

    fd = stream.fileno()
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        ready, _, _ = select.select([fd], [], [], remaining)
        if not ready:
            return None
        try:
            chunk = os.read(fd, 65536)
        except (BlockingIOError, InterruptedError):
            continue
        except OSError:
            chunk = b""
        if not chunk:  # EOF
            if buf:
                # Unterminated remainder at EOF — surface it as the final line so
                # a SUT that forgot the trailing newline still gets parsed.
                data = bytes(buf)
                buf.clear()
                return data.decode("utf-8", errors="replace")
            return ""
        buf.extend(chunk)
        nl = buf.find(b"\n")
        if nl != -1:
            return _pop_line(buf, nl)


def _pop_line(buf: bytearray, nl: int) -> str:
    """Pop bytes through the newline at index `nl` (inclusive) off `buf`,
    mutating it in place so the surplus persists for the next call."""
    line = bytes(buf[: nl + 1])
    del buf[: nl + 1]
    return line.decode("utf-8", errors="replace")


def _force_remove_container(handle: SUTHandle) -> None:
    """Best-effort `docker rm -f` of the SUT's container.

    Killing the `docker run` client process does not reliably stop the
    container, so on a containerised RESET/shutdown we remove it by name. Any
    failure (already gone, no daemon) is swallowed — this is cleanup, and the
    `--rm` flag already handles the happy path."""
    if not handle.container_name:
        return
    try:
        subprocess.run(
            ["docker", "rm", "-f", handle.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        pass


def _killpg(proc: subprocess.Popen) -> None:
    """SIGKILL the process's entire group, falling back to the direct child.

    The SUT is spawned with ``start_new_session=True``, so it leads its own
    process group whose id equals its pid; signalling that group takes any
    children (agent-scaffold helpers, socket servers) with it. If the group is
    already gone, or setsid somehow didn't take, fall back to the direct pid so
    we never accidentally signal the harness's own group.
    """
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.send_signal(signal.SIGKILL)
        except ProcessLookupError:
            pass


def kill_sut(handle: SUTHandle, timeout_s: float = 2.0) -> tuple[str, Optional[int]]:
    """Kill the SUT process *group*. Returns (signal_name, exit_code).

    Per the brief: `RESET` is SIGKILL + wait, not graceful shutdown. Because the
    SUT leads its own process group (`start_new_session=True` at spawn), we
    `killpg` so any children it spawned die with it — otherwise a surviving
    helper (e.g. a socket server the respawned SUT reconnects to) could carry
    in-memory state across the discontinuity. For a containerised SUT we also
    `docker rm -f` the container by name, since killing the `docker run` client
    alone may leave the container running.
    """
    proc = handle.process
    # Close stdin first so a well-behaved SUT could exit on EOF; we don't wait.
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass

    sig_name = "SIGKILL"
    # Signal the group unconditionally, not only while the leader is alive: a
    # crashed leader (mid-run crash path) may have exited leaving children
    # behind, and the pgid stays valid as long as any member survives. _killpg
    # degrades to a no-op if the whole group is already gone.
    _killpg(proc)
    try:
        exit_code = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        exit_code = None  # truly unresponsive; harness gives up waiting.
    _force_remove_container(handle)
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
        _force_remove_container(handle)
        return "EOF", exit_code
    except subprocess.TimeoutExpired:
        return kill_sut(handle, timeout_s=timeout_s)


def parse_command(cmd: str | list[str]) -> list[str]:
    if isinstance(cmd, list):
        return list(cmd)
    return shlex.split(cmd)
