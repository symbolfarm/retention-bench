"""B4a: harness docker-run launch path.

Two layers:
  - Pure-function tests for `build_docker_argv` + `host_path_for_mount` and the
    `_make_container_spec` manifest wiring. These run everywhere and carry the
    real coverage of the argv-construction / path-translation logic.
  - A docker-gated integration test that actually round-trips a containerised
    echo SUT through the harness (skipped when no docker daemon is reachable).
    B4c's smoke test is the authoritative end-to-end validation; this is a
    cheap regression guard for the launch/RESET lifecycle on the docker path.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from harness import event_loop, sut_process
from harness.sut_process import (
    DIR_CONTAINER_PATH,
    SHIM_CONTAINER_PATH,
    ContainerSpec,
    SUTError,
    build_docker_argv,
    host_path_for_mount,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


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


# --- _make_container_spec (manifest wiring) ------------------------------


def _config(manifest):
    # Minimal RunConfig stand-in: _make_container_spec only reads sut_manifest.
    return event_loop.RunConfig(
        task=None,  # unused by _make_container_spec
        sut_command=["python", "-m", "no_state"],
        runs_root=REPO_ROOT / "runs",
        sut_manifest=manifest,
    )


def test_no_container_spec_without_image():
    """A manifest without `image` keeps the subprocess path (spec is None)."""
    cfg = _config({"entrypoint": ["python", "-m", "no_state"], "env": ["X"]})
    assert event_loop._make_container_spec(cfg, "run", REPO_ROOT / "d", 0) is None


def test_no_container_spec_without_manifest():
    cfg = _config(None)
    assert event_loop._make_container_spec(cfg, "run", REPO_ROOT / "d", 0) is None


def test_container_spec_built_from_manifest(monkeypatch):
    monkeypatch.delenv("HOST_WORKSPACE", raising=False)
    monkeypatch.delenv("RETENTION_BENCH_SHIM_DIR", raising=False)
    cfg = _config({
        "image": "retention-bench/no-state:latest",
        "entrypoint": ["python", "-m", "no_state"],
        "env": ["OPENROUTER_API_KEY", "NO_STATE_MODEL"],
    })
    dir_path = REPO_ROOT / "runs" / "r" / "dir"
    spec = event_loop._make_container_spec(cfg, "run-xyz", dir_path, 2)
    assert spec is not None
    assert spec.image == "retention-bench/no-state:latest"
    assert spec.container_name == "retbench-run-xyz-02"  # unique per invocation
    assert spec.env_names == ["OPENROUTER_API_KEY", "NO_STATE_MODEL"]
    assert spec.shim_host_path is None


def test_container_spec_includes_shim_when_env_set(monkeypatch):
    monkeypatch.delenv("HOST_WORKSPACE", raising=False)
    shim = REPO_ROOT / "tests" / "fake_openai_shim"
    monkeypatch.setenv("RETENTION_BENCH_SHIM_DIR", str(shim))
    cfg = _config({"image": "img:latest", "env": []})
    spec = event_loop._make_container_spec(cfg, "run", REPO_ROOT / "d", 0)
    assert spec.shim_host_path == str(shim)


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
        reply = sut_process.send_event(handle, "evt-0001", "READ", "hello", timeout_s=60)
        assert reply["event_id"] == "evt-0001"
    finally:
        sut_process.kill_sut(handle)
    # Container removed by name.
    out = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=retbench-pytest-roundtrip", "-q"],
        capture_output=True, text=True,
    )
    assert out.stdout.strip() == ""
