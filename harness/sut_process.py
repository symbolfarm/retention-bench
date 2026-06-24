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


def kill_sut(handle: SUTHandle, timeout_s: float = 2.0) -> tuple[str, Optional[int]]:
    """Kill the SUT process. Returns (signal_name, exit_code).

    Per the brief: `RESET` is SIGKILL + wait, not graceful shutdown. For a
    containerised SUT we also `docker rm -f` the container by name, since
    killing the `docker run` client alone may leave the container running.
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
