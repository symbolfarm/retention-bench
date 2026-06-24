"""Subprocess-mode launch normalisation.

In subprocess mode the manifest `entrypoint`'s `python`/`python3` token names the
*container* interpreter; on the host the harness must launch under its own
interpreter (`sys.executable`) so the SUT (a) finds an interpreter that exists
and (b) runs under the same venv/deps as the harness. Non-python entrypoints are
left untouched. Container mode is covered by test_docker_launch.
"""

from __future__ import annotations

import sys
from pathlib import Path

from harness import sut_process


class _FakePopen:
    """Captures the argv it was constructed with; no real process is spawned."""

    last_argv: list[str] | None = None

    def __init__(self, argv, **kwargs):
        type(self).last_argv = list(argv)


def _spawn(monkeypatch, tmp_path: Path, command: list[str]) -> list[str]:
    monkeypatch.setattr(sut_process.subprocess, "Popen", _FakePopen)
    _FakePopen.last_argv = None
    sut_process.spawn_sut(command, dir_path=tmp_path, invocation_index=0)
    assert _FakePopen.last_argv is not None
    return _FakePopen.last_argv


def test_python_entrypoint_launched_under_sys_executable(monkeypatch, tmp_path):
    argv = _spawn(monkeypatch, tmp_path, ["python", "-m", "no_state"])
    assert argv == [sys.executable, "-m", "no_state"]


def test_python3_entrypoint_launched_under_sys_executable(monkeypatch, tmp_path):
    argv = _spawn(monkeypatch, tmp_path, ["python3", "-m", "no_state"])
    assert argv == [sys.executable, "-m", "no_state"]


def test_non_python_entrypoint_is_untouched(monkeypatch, tmp_path):
    argv = _spawn(monkeypatch, tmp_path, ["/opt/sut/bin/run", "--serve"])
    assert argv == ["/opt/sut/bin/run", "--serve"]
