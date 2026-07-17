"""RB-10: SubprocessSystem._exchange kills on timeout and surfaces crashes.

Finding 2 of the 2026-07-07 review: the docs say a timeout SIGKILLs the SUT, but
``_exchange`` only raised — the wedged process lived until shutdown()/GC. These
tests drive ``respond()`` against deliberately-misbehaving SUTs and assert:

  * a SUT that never replies raises ``SUTTimeout`` *and* its whole process group
    (including a spawned child) is dead and the handle dropped; and
  * a SUT that closes stdout without replying (mid-run crash) raises a clear
    ``SUTError`` and is likewise reaped.

Requires the ``cl-benchmark`` distribution (import path ``src``); skipped where
it is absent, like ``test_subprocess_system``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from pydantic import BaseModel  # noqa: E402
from src.interface import Query  # noqa: E402

from harness import sut_process  # noqa: E402
from retention_bench import SubprocessSystem  # noqa: E402


class _Ack(BaseModel):
    ok: bool = True


def _query() -> Query:
    return Query(
        prompt="anything",
        response_schema=_Ack,
        instance_id="inst-0",
        instance_index=0,
    )


# A SUT that spawns a long-lived child, records both pids, then wedges (never
# reads stdin, never replies) — the timeout path must SIGKILL the whole group.
_WEDGE_SUT = r"""
import json, os, subprocess, sys, time
from pathlib import Path

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
Path("pids.json").write_text(json.dumps({"child": child.pid}))
sys.stdout.write("")  # ensure stdout is opened; do not reply
sys.stdout.flush()
time.sleep(300)
"""

# A SUT that reads one line then exits non-zero without replying (mid-run crash).
_CRASH_SUT = r"""
import sys
line = sys.stdin.readline()
sys.exit(3)
"""


def _proc_alive(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat") as fh:
            data = fh.read()
    except (FileNotFoundError, ProcessLookupError):
        return False
    return data[data.rindex(")") + 2] in ("R", "S", "D")


def test_exchange_timeout_kills_sut_and_its_group(tmp_path):
    sut_file = tmp_path / "wedge_sut.py"
    sut_file.write_text(_WEDGE_SUT)
    system = SubprocessSystem(
        ["python", str(sut_file)],
        tmp_path / "state",
        name="wedge",
        timeout_s=0.5,
    )
    try:
        with pytest.raises(sut_process.SUTTimeout):
            system.respond(_query())

        # The wedged SUT and its child must both be gone — no survivor lingering
        # until shutdown()/GC, and the handle is dropped so respond() respawns.
        assert system._handle is None
        pids = json.loads((system._state_dir / "pids.json").read_text())
        deadline = time.monotonic() + 3.0
        while _proc_alive(pids["child"]) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not _proc_alive(pids["child"]), "child survived the timeout kill"
    finally:
        system.shutdown()


def test_exchange_surfaces_mid_run_crash(tmp_path):
    sut_file = tmp_path / "crash_sut.py"
    sut_file.write_text(_CRASH_SUT)
    system = SubprocessSystem(
        ["python", str(sut_file)],
        tmp_path / "state",
        name="crash",
        timeout_s=5.0,
    )
    try:
        with pytest.raises(sut_process.SUTError) as exc:
            system.respond(_query())
        assert "closed stdout" in str(exc.value)
        assert system._handle is None
    finally:
        system.shutdown()
