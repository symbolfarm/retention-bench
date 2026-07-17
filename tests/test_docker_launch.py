"""B4a: SUT docker-run launch path (the ``harness.sut_process`` container primitives).

Two layers:
  - Pure-function tests for `build_docker_argv` + `host_path_for_mount`. These
    run everywhere and carry the real coverage of the argv-construction /
    path-translation logic that `retention_bench.SubprocessSystem`'s container
    mode rides on.
  - A docker-gated integration test that actually round-trips a containerised
    echo SUT (skipped when no docker daemon is reachable) — a cheap regression
    guard for the launch/RESET lifecycle on the docker path.

(The book-track ``event_loop._make_container_spec`` manifest-wiring tests were
retired with the book-track harness by C20; the argv/teardown primitives they
exercised live in ``sut_process`` and are covered above.)
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from harness import sut_process
from harness.sut_process import (
    DIR_CONTAINER_PATH,
    SHIM_CONTAINER_PATH,
    ContainerSpec,
    SUTError,
    SUTHandle,
    SUTTimeout,
    build_docker_argv,
    host_path_for_mount,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _send_event(
    handle: "SUTHandle",
    event_id: str,
    event_type: str,
    stage_input: str,
    timeout_s: float = 300.0,
) -> dict[str, Any]:
    """Test-only helper: speak the retired book-track READ/QUIZ framing.

    Demoted from ``harness.sut_process.send_event`` (removed as dead code on
    the live path — RB-13/2026-07-07 review "Book-track residue" — the live
    ``SubprocessSystem`` speaks its own per-instance JSON contract, see
    ``retention_bench.system._exchange``). Kept here only so the docker
    round-trip test below can still drive the inline echo SUT, which speaks
    this shape, over the real spawn/kill launch path.
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
    reply = sut_process._readline_with_timeout(handle.process.stdout, timeout_s)
    if reply is None:
        raise SUTTimeout(f"SUT did not respond to {event_id} within {timeout_s:.0f}s")
    if not reply:
        rc = handle.process.poll()
        raise SUTError(f"SUT closed stdout before replying to {event_id} (exit={rc})")
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
            raise SUTError(f"SUT QUIZ reply for {event_id} missing 'answers' list: {parsed!r}")
        if not isinstance(parsed["answers"], list):
            raise SUTError(f"SUT QUIZ reply 'answers' for {event_id} must be a list: {parsed!r}")
    return parsed


# --- host_path_for_mount -------------------------------------------------


def test_host_path_unchanged_without_host_workspace(monkeypatch):
    monkeypatch.delenv("HOST_WORKSPACE", raising=False)
    p = REPO_ROOT / "runs" / "abc" / "dir"
    assert host_path_for_mount(p, REPO_ROOT) == str(p)


def test_host_path_translated_under_host_workspace(monkeypatch):
    monkeypatch.setenv("HOST_WORKSPACE", "/host/ws")
    p = REPO_ROOT / "runs" / "abc" / "dir"
    # repo-root prefix swapped for HOST_WORKSPACE, relative tail preserved.
    assert host_path_for_mount(p, REPO_ROOT) == "/host/ws/runs/abc/dir"


def test_host_path_raises_when_outside_repo_with_host_workspace(monkeypatch):
    monkeypatch.setenv("HOST_WORKSPACE", "/host/ws")
    with pytest.raises(SUTError, match="not under the repo root"):
        host_path_for_mount(Path("/tmp/somewhere/else"), REPO_ROOT)


# --- build_docker_argv ---------------------------------------------------


def _spec(**over) -> ContainerSpec:
    base = dict(
        image="retention-bench/no-state:latest",
        container_name="retbench-run-00",
        dir_host_path="/host/ws/runs/r/dir",
        env_names=["OPENROUTER_API_KEY", "NO_STATE_MODEL"],
        shim_host_path=None,
    )
    base.update(over)
    return ContainerSpec(**base)


def test_docker_argv_core_shape():
    argv = build_docker_argv(_spec(), ["python", "-m", "no_state"])
    assert argv[:4] == ["docker", "run", "-i", "--rm"]
    assert "--name" in argv and "retbench-run-00" in argv
    # DIR bind-mounted at the fixed container path, and it's the workdir.
    assert f"/host/ws/runs/r/dir:{DIR_CONTAINER_PATH}" in argv
    assert argv[argv.index("-w") + 1] == DIR_CONTAINER_PATH
    assert f"RETENTION_BENCH_DIR={DIR_CONTAINER_PATH}" in argv
    # Image precedes the entrypoint, which is appended verbatim at the tail.
    assert argv[-4:] == ["retention-bench/no-state:latest", "python", "-m", "no_state"]


def test_docker_argv_forwards_env_by_name_only():
    """Secret values must never appear in argv — only `-e NAME` (no `=value`)."""
    argv = build_docker_argv(_spec(), ["python", "-m", "no_state"])
    # Each declared var appears as a bare name immediately after a `-e`.
    for name in ("OPENROUTER_API_KEY", "NO_STATE_MODEL"):
        assert name in argv
        assert argv[argv.index(name) - 1] == "-e"
        # No `NAME=value` form for the forwarded vars.
        assert not any(tok.startswith(f"{name}=") for tok in argv)


def test_docker_argv_shim_mount_when_requested():
    argv = build_docker_argv(
        _spec(shim_host_path="/host/ws/tests/fake_openai_shim"),
        ["python", "-m", "no_state"],
    )
    assert f"/host/ws/tests/fake_openai_shim:{SHIM_CONTAINER_PATH}:ro" in argv
    assert f"PYTHONPATH={SHIM_CONTAINER_PATH}" in argv


def test_docker_argv_no_shim_by_default():
    argv = build_docker_argv(_spec(), ["python", "-m", "no_state"])
    assert not any("PYTHONPATH" in tok for tok in argv)
    assert SHIM_CONTAINER_PATH not in " ".join(argv)


# --- docker round-trip (skipped without a daemon) ------------------------

_DOCKER_OK = shutil.which("docker") is not None and (
    subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0
)

# A self-contained echo SUT as an inline script: implements the minimal
# READ/QUIZ wire contract so we can validate the launch + RESET lifecycle on
# the docker path without depending on B4b's images.
_ECHO_SUT = (
    "import sys, json\n"
    "for line in sys.stdin:\n"
    "    line = line.strip()\n"
    "    if not line:\n"
    "        continue\n"
    "    ev = json.loads(line)\n"
    "    out = {'event_id': ev['event_id']}\n"
    "    if ev.get('event_type') == 'QUIZ':\n"
    "        out['answers'] = []\n"
    "    else:\n"
    "        out['stage_output'] = ''\n"
    "    sys.stdout.write(json.dumps(out) + '\\n'); sys.stdout.flush()\n"
)


@pytest.mark.skipif(not _DOCKER_OK, reason="no reachable docker daemon")
def test_docker_round_trip(tmp_path):
    """Launch a containerised echo SUT, exchange one event, then kill it and
    confirm the container is gone (RESET teardown via docker rm -f)."""
    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    spec = ContainerSpec(
        image="python:3.11-slim",
        container_name="retbench-pytest-roundtrip",
        dir_host_path=str(dir_path),  # no HOST_WORKSPACE here: daemon shares fs
        env_names=[],
    )
    handle = sut_process.spawn_sut(
        ["python", "-c", _ECHO_SUT],
        dir_path=dir_path,
        invocation_index=0,
        container=spec,
    )
    try:
        reply = _send_event(handle, "evt-0001", "READ", "hello", timeout_s=60)
        assert reply["event_id"] == "evt-0001"
    finally:
        sut_process.kill_sut(handle)
    # Container removed by name.
    out = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=retbench-pytest-roundtrip", "-q"],
        capture_output=True, text=True,
    )
    assert out.stdout.strip() == ""
