"""Production ``SubprocessSystem``: a process-contract SUT as a CL-Bench system.

This is the C2 adapter the C0 spike prototyped. It wraps an arbitrary subprocess
SUT (spawn/kill reused verbatim from ``harness.sut_process``) as a CL-Bench
``ContinualLearningSystem``, and adds the two things CL-Bench has no native way
to express:

  * a **hard RESET** — SIGKILL + respawn where *only the on-disk survive-dir
    persists* (no graceful flush, no in-memory carry-over); and
  * a **system-side reset schedule** — arbitrary reset density ``k`` over the
    run, owned here rather than by the runner's all-or-nothing
    ``reset_between_instances`` boolean (see ``reset_schedule``).

It also emits CL-Bench ``UsageEvent``s tagged ``call_type="compute"`` so a
parametric/constructive SUT's FLOPs and the survive-dir storage footprint land
in the same accounting channel the framework already records per step.

### SUT process contract (one JSON line each way)

Request (harness → SUT)::

    {"prompt": str,
     "instance_id": str|null,
     "instance_index": int|null,
     "response_schema": {<JSON Schema of the query's response model>},
     "feedback": str|null}

Reply (SUT → harness)::

    {"action": {<fields matching response_schema>},
     "resource": {"flops": int, "tokens_in": int, "tokens_out": int,
                  "model_id": str, ...}}            # resource optional

``action`` may be omitted if the whole reply object (minus the reserved
``resource`` key) *is* the action — a convenience for trivial SUTs. ``resource``
is free-form self-report; recognised keys (``flops``, ``tokens_in``,
``tokens_out``, ``model_id``) are lifted onto the compute ``UsageEvent`` and the
entire dict is preserved under ``metadata["sut_resource"]``.

This deliberately does **not** reuse ``harness.sut_process.send_event``: that
helper hard-codes the book-track ``READ``/``QUIZ`` → ``answers:[{id,text}]``
framing, which cannot carry CL-Bench's arbitrary per-query ``response_schema``.
We reuse the *process lifecycle* (spawn/kill) and define our own framing.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Optional

from harness import dir_lifecycle, sut_process

from ._clbench import (
    ContinualLearningSystem,
    Observation,
    Query,
    Response,
    UsageEvent,
    observation_marks_instance_complete,
)
from .reset_schedule import NoReset, ResetSchedule

_RESERVED_REPLY_KEY = "resource"


class SubprocessSystem(ContinualLearningSystem):
    """Drive a subprocess SUT through CL-Bench's runner with a hard reset.

    Args:
        command: argv to launch the SUT (e.g. ``["python", "-m", "my_sut"]`` or
            ``["python", "/abs/path/sut.py"]``). Reused launch semantics from
            ``harness.sut_process.spawn_sut``: cwd is the survive-dir,
            ``RETENTION_BENCH_DIR`` is exported, and a ``python``/``python3``
            argv[0] is rewritten to the harness interpreter.
        state_dir: the survive-dir. The *only* thing that persists across a hard
            reset. Created if absent.
        reset_schedule: when to hard-bounce between instances (default
            :class:`NoReset` — the stateful ceiling).
        name: system name (leaderboard row / trace label).
        wipe_on_reset: if True, delete the survive-dir contents on every hard
            reset — the stateless baseline arm (no retention possible). Default
            False (retention: state survives the SIGKILL on disk).
        timeout_s: per-response wall-clock timeout.
        extra_pythonpath: extra dirs prepended to the SUT's PYTHONPATH.
        stderr_log: optional file to capture SUT stderr.
    """

    def __init__(
        self,
        command: list[str],
        state_dir: Path,
        *,
        reset_schedule: ResetSchedule = NoReset(),
        name: str = "subprocess",
        wipe_on_reset: bool = False,
        timeout_s: float = 300.0,
        extra_pythonpath: Optional[list[Path]] = None,
        stderr_log: Optional[Path] = None,
    ) -> None:
        self._command = list(command)
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._schedule = reset_schedule
        self._name = name
        self._wipe_on_reset = wipe_on_reset
        self._timeout_s = timeout_s
        self._extra_pythonpath = extra_pythonpath
        self._stderr_log = stderr_log

        self._handle: Optional[sut_process.SUTHandle] = None
        self._completed_instances = 0
        self._last_storage_bytes, _ = dir_lifecycle.account_dir(self._state_dir)

        # Observability counters (asserted by tests; surfaced for C4 reporting).
        self.spawns = 0
        self.kills = 0
        self.scheduled_resets = 0

    # -- lifecycle ---------------------------------------------------------- #

    def _spawn(self) -> None:
        self._handle = sut_process.spawn_sut(
            self._command,
            dir_path=self._state_dir,
            invocation_index=self.spawns,
            stderr_log=self._stderr_log,
            extra_pythonpath=self._extra_pythonpath,
        )
        self.spawns += 1

    def _hard_bounce(self) -> None:
        """SIGKILL the SUT (if alive) and drop the handle; survive-dir is kept.

        Respawn is lazy — the next ``respond()`` spins a fresh process that sees
        only what is on disk. No event is emitted here; emission is the caller's
        responsibility (the runner discards events from the start-of-run
        ``reset()``, so only ``observe()``-driven bounces should record one).
        """
        if self._handle is not None:
            sut_process.kill_sut(self._handle)
            self.kills += 1
            self._handle = None
        if self._wipe_on_reset:
            self._wipe_survive_dir()

    def _wipe_survive_dir(self) -> None:
        """Stateless-baseline arm: clear everything except the reserved prefix."""
        for entry in self._state_dir.iterdir():
            if entry.name == dir_lifecycle.HARNESS_RESERVED_PREFIX:
                continue
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
        self._last_storage_bytes = 0

    # -- CL-Bench ContinualLearningSystem interface ------------------------- #

    def respond(self, query: Query) -> Response:
        if self._handle is None:
            self._spawn()
        assert self._handle is not None

        request = {
            "prompt": query.prompt,
            "instance_id": query.instance_id,
            "instance_index": query.instance_index,
            "response_schema": query.response_schema.model_json_schema(),
            "feedback": query.feedback.content if query.feedback is not None else None,
        }
        reply = self._exchange(request)

        action_fields, resource = _split_reply(reply)
        action = query.response_schema(**action_fields)
        self._emit_compute_event(resource, query)
        return Response(action=action, metadata={"sut_resource": resource} if resource else None)

    def observe(self, observation: Observation, next_query: Optional[Query] = None) -> None:
        if not observation_marks_instance_complete(observation):
            return
        self._completed_instances += 1

        # Storage footprint of the survive-dir after this instance's writes —
        # the bytes that must survive a hard reset. Measured before any bounce
        # (the kill cannot change on-disk state).
        cur_bytes, file_count = dir_lifecycle.account_dir(self._state_dir)
        storage_delta = cur_bytes - self._last_storage_bytes
        self._last_storage_bytes = cur_bytes

        will_reset = next_query is not None and self._schedule.should_reset(
            self._completed_instances
        )
        if will_reset:
            self._hard_bounce()
            self.scheduled_resets += 1

        self.record_usage_event(
            UsageEvent(
                call_type="compute",
                model=self._name,
                metadata={
                    "kind": "storage",
                    "instance_ordinal": self._completed_instances,
                    "survive_dir_bytes": cur_bytes,
                    "survive_dir_delta_bytes": storage_delta,
                    "survive_dir_file_count": file_count,
                    "reset": will_reset,
                    "schedule": self._schedule.label,
                    "cumulative_hard_kills": self.kills,
                },
            )
        )

    def reset(self) -> None:
        """CL-Bench reset hook = hard process bounce keeping the survive-dir.

        Called by the runner once at start (``reset_system``) and, if the caller
        sets ``reset_between_instances=True``, after every instance. We drive
        density from :meth:`observe` instead, so in normal use this fires only
        at start (a no-op bounce: no handle yet). It deliberately emits no usage
        event — the runner discards events from the start reset.
        """
        self._hard_bounce()

    @property
    def name(self) -> str:
        return self._name

    # -- internals ---------------------------------------------------------- #

    def _exchange(self, request: dict[str, Any]) -> dict[str, Any]:
        assert self._handle is not None
        proc = self._handle.process
        line = json.dumps(request, ensure_ascii=False) + "\n"
        try:
            assert proc.stdin is not None
            proc.stdin.write(line)
            proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise sut_process.SUTError(
                f"failed writing to SUT stdin for instance "
                f"{request.get('instance_id')}: {exc}"
            ) from exc

        assert proc.stdout is not None
        reply_line = sut_process._readline_with_timeout(proc.stdout, self._timeout_s)
        if reply_line is None:
            raise sut_process.SUTTimeout(
                f"SUT did not respond to instance {request.get('instance_id')} "
                f"within {self._timeout_s:.0f}s"
            )
        if not reply_line:
            rc = proc.poll()
            raise sut_process.SUTError(
                f"SUT closed stdout before replying to instance "
                f"{request.get('instance_id')} (exit={rc})"
            )
        try:
            return json.loads(reply_line)
        except json.JSONDecodeError as exc:
            raise sut_process.SUTError(
                f"SUT reply for instance {request.get('instance_id')} "
                f"is not valid JSON: {exc}: {reply_line!r}"
            ) from exc

    def _emit_compute_event(self, resource: dict[str, Any], query: Query) -> None:
        """Record the per-respond compute event (SUT-self-reported FLOPs/tokens).

        For a no-state or counter SUT ``resource`` is empty and this still
        records a zero-cost compute marker, keeping one compute event per
        response regardless of SUT class. A constructive SUT (C3) populates
        ``flops``/``param_count``/etc. and they flow straight through.
        """
        tokens_in = _opt_int(resource.get("tokens_in"))
        tokens_out = _opt_int(resource.get("tokens_out"))
        model = resource.get("model_id") if isinstance(resource.get("model_id"), str) else self._name
        self.record_usage_event(
            UsageEvent(
                call_type="compute",
                model=model or self._name,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                metadata={
                    "kind": "respond",
                    "instance_id": query.instance_id,
                    "instance_index": query.instance_index,
                    "flops": _opt_int(resource.get("flops")),
                    "sut_resource": resource,
                },
            )
        )


def _split_reply(reply: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(action_fields, resource)`` from a SUT reply.

    Prefer an explicit ``action`` object; otherwise treat the whole reply (minus
    the reserved ``resource`` key) as the action fields.
    """
    if not isinstance(reply, dict):
        raise sut_process.SUTError(f"SUT reply must be a JSON object, got {type(reply).__name__}")
    resource = reply.get(_RESERVED_REPLY_KEY) or {}
    if not isinstance(resource, dict):
        raise sut_process.SUTError(f"SUT reply 'resource' must be an object, got {resource!r}")
    if "action" in reply:
        action = reply["action"]
        if not isinstance(action, dict):
            raise sut_process.SUTError(f"SUT reply 'action' must be an object, got {action!r}")
        return action, resource
    return {k: v for k, v in reply.items() if k != _RESERVED_REPLY_KEY}, resource


def _opt_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
