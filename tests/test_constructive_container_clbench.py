"""C9: drive the *containerised* constructive SUT through CL-Bench's runner.

The container analogue of ``test_constructive_clbench.py``. Same headline claim
— a constructive system run as a Continual Learning Bench system under a hard
reset — but the SUT runs inside its docker image
(``retention-bench/sut-constructive:0.1``) launched via the B4a engine, not as a
bare host subprocess. The load-bearing C9 assertions:

  * ``SubprocessSystem`` launches the SUT in a container (``ContainerLaunch``)
    and the container speaks the C2 wire protocol (``constructive.clbench_main``,
    the manifest's ``clbench_entrypoint`` — the only launch argv the live path
    consumes);
  * the hard RESET tears the **container** down (``docker rm -f`` by name) and
    nothing is left running;
  * parametric state in the bind-mounted survive-dir (``/dir``) *survives the
    container kill*: a fresh post-reset container loads the grown checkpoint, so
    the lineage's ``read_count`` spans every instance across the SIGKILLs.

This test does **not** build the image (a ~1.3GB torch build); it skips unless
the image is already present locally. Build it with::

    docker build -f suts/sut-torch-cpu-base.Dockerfile \\
        -t retention-bench/sut-torch-cpu-base:0.1 suts/
    docker build -t retention-bench/sut-constructive:0.1 suts/constructive/

so the always-on suite stays green on a daemon-less / unbuilt host.
"""
from __future__ import annotations

import subprocess
import tempfile
from shutil import which
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")
pytest.importorskip("torch", reason="torch not installed")

import torch  # noqa: E402

from retention_bench import ContainerLaunch, EveryNInstances, SubprocessSystem  # noqa: E402
from src.runtime.runner import run_task  # noqa: E402
from src.tasks.blind_spectrum_monitoring.task import (  # noqa: E402
    BlindSpectrumMonitoringTask,
)

IMAGE = "retention-bench/sut-constructive:0.1"
# The CL-Bench wire entrypoint, matching the manifest's `clbench_entrypoint`.
CLBENCH_CMD = ["python", "-m", "constructive.clbench_main"]
VARIANT = "five_ch_wide"  # 13 latent channels; no on-disk corpus needed.
BASE_LAYERS = 1
# The tiny-model knobs the SUT reads; forwarded by name into the container.
TINY_ENV = {
    "CONSTRUCTIVE_BLOCK_SIZE": "32",
    "CONSTRUCTIVE_D_MODEL": "16",
    "CONSTRUCTIVE_N_HEADS": "2",
    "CONSTRUCTIVE_N_LAYERS": str(BASE_LAYERS),
    "CONSTRUCTIVE_SEED": "0",
}


def _docker_ok() -> bool:
    if which("docker") is None:
        return False
    if not subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0:
        return False
    # Image must already be built (we don't build a 1.3GB image in-test).
    out = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out.returncode == 0


_DOCKER_AND_IMAGE = _docker_ok()
pytestmark = pytest.mark.skipif(
    not _DOCKER_AND_IMAGE,
    reason=f"docker daemon and {IMAGE} both required (build the image; see module docstring)",
)


@pytest.fixture(autouse=True)
def _container_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the tiny-model knobs in the *host* env (forwarded into the container
    by name via ``ContainerLaunch.env_names``) and ensure HOST_WORKSPACE is
    unset so the Sysbox shared-fs bind-mount path translation is a no-op."""
    for k, v in TINY_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("HOST_WORKSPACE", raising=False)


def _make_system(state_dir: Path) -> SubprocessSystem:
    return SubprocessSystem(
        CLBENCH_CMD,
        state_dir,
        reset_schedule=EveryNInstances(2),
        name="constructive-container",
        container=ContainerLaunch(image=IMAGE, env_names=list(TINY_ENV)),
    )


def _load_meta(state_dir: Path) -> dict:
    blob = torch.load(state_dir / "checkpoint.pt", map_location="cpu", weights_only=False)
    return {"config": blob["config"], "meta": blob["meta"]}


def _containers_with(token: str) -> list[str]:
    out = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={token}", "-q"],
        capture_output=True,
        text=True,
    )
    return [c for c in out.stdout.split() if c]


def test_constructive_container_runs_and_survives_reset():
    """The containerised constructive SUT runs through CL-Bench under a hard
    reset; the container is killed + removed at each reset, yet parametric state
    in the bind-mounted survive-dir carries across the kills."""
    state_dir = Path(tempfile.mkdtemp(prefix="c9-container-"))
    system = _make_system(state_dir)
    token = system._run_token
    task = BlindSpectrumMonitoringTask(variant=VARIANT, num_instances=6, probe_mode=True)

    from src.interface import TaskResult

    with system:  # shutdown() reaps the final (un-bounced) container on exit
        result = run_task(task, system, show_progress=False, reset_between_instances=False)

        # Ran end-to-end through the runner.
        assert isinstance(result, TaskResult)
        assert 0.0 <= result.score <= 1.0  # gibberish-driven; presence is the claim

        # The hard reset actually fired: 2 bounces over 6 instances (after #2 and
        # #4), so 3 container launches and 2 container kills.
        assert system.scheduled_resets == 2
        assert system.kills == 2
        assert system.spawns == 3

        # State survived the container kills: a fresh post-reset container loaded
        # the grown checkpoint (else load_state_dict would mismatch and crash),
        # and one lineage trained on every instance across the SIGKILLs.
        meta = _load_meta(state_dir)
        assert meta["config"]["n_layers"] == BASE_LAYERS + 1  # grew exactly once
        assert meta["meta"]["growth_count"] == 1
        assert meta["meta"]["read_count"] == 6  # all instances seen by one lineage

    # Teardown is clean: the RESET docker-rm-f's each bounced container, and the
    # context-manager exit reaps the final one — no container for this run's
    # token is left behind. The token namespaces this instance's containers.
    assert _containers_with(token) == []
