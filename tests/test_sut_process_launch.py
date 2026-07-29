"""Subprocess-mode launch normalisation.

In subprocess mode a `command`'s `python`/`python3` token names the *container*
interpreter (the same argv works for container mode, where it resolves inside
the image); on the host the harness must launch under its own interpreter
(`sys.executable`) so the SUT (a) finds an interpreter that exists and (b) runs
under the same venv/deps as the harness. Non-python commands are left
untouched. Container mode is covered by test_docker_launch.
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


def test_explicit_interpreter_path_is_honoured(monkeypatch, tmp_path):
    """An explicit path is a deliberate interpreter choice — do not rewrite it.

    Found while wiring constructive-retention's `--mode constructed-hop2` through the
    harness (CR-29): the SUT declared `.../constructive-retention/.venv/bin/python`
    and `ps` showed it running under retention-bench's venv instead. It only worked
    because that venv happened to have torch+CUDA, and it defeats the environment
    isolation the process-level SUT contract promises.
    """
    explicit = "/opt/other-project/.venv/bin/python"
    argv = _spawn(monkeypatch, tmp_path, [explicit, "-m", "some_sut"])
    assert argv == [explicit, "-m", "some_sut"]


def test_relative_interpreter_path_is_honoured(monkeypatch, tmp_path):
    argv = _spawn(monkeypatch, tmp_path, ["./.venv/bin/python3", "-m", "some_sut"])
    assert argv == ["./.venv/bin/python3", "-m", "some_sut"]
