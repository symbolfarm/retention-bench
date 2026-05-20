"""Event loop: drive a task definition end-to-end against a SUT subprocess.

Per docs/trace-schema.md and docs/task-definition-schema.md. Thin harness
(decision #7-D): does not interpret SUT output as tool-call directives.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import __version__ as HARNESS_VERSION
from . import dir_lifecycle, sut_process, trace_writer
from .task_loader import Event, Question, TaskDefinition


@dataclass
class RunConfig:
    task: TaskDefinition
    sut_command: list[str]
    runs_root: Path
    run_id: Optional[str] = None  # auto-generated if None
    harness_commit: str = "unknown"
    keep_dir: bool = True  # default per brief: keep for inspection
    event_timeout_s: float = 300.0  # 5 min default per M4
    sut_manifest: Optional[dict] = None  # read from <sut_dir>/sut-manifest.json by CLI
    sut_pythonpath: list[Path] = field(default_factory=list)  # added to spawned PYTHONPATH


def _iso_now() -> str:
    # ms precision, UTC, Z suffix
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:6]


def _gen_run_id(task_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{task_id}-{ts}-{_short_hash(ts + task_id + str(os.getpid()))}"


def _ms_between(t0: float, t1: float) -> int:
    return int(round((t1 - t0) * 1000))


def _render_read_input(event_id: str, material_id: str, text: str) -> str:
    return (
        "<META>\n"
        f"type: read\n"
        f"event_id: {event_id}\n"
        f"material_id: {material_id}\n"
        "</META>\n"
        "<TEXT>\n"
        f"{text}\n"
        "</TEXT>\n"
    )


def _render_quiz_input(
    event_id: str,
    probe: str,
    k: Optional[int],
    questions: list[Question],
) -> str:
    meta_lines = [
        "<META>",
        "type: quiz",
        f"probe: {probe}",
        f"event_id: {event_id}",
    ]
    if k is not None:
        meta_lines.append(f"k: {k}")
    meta_lines.append("</META>")
    q_lines = ["<QUESTIONS>"]
    for q in questions:
        q_lines.append(f'<QUESTION id="{q.id}">{q.text}</QUESTION>')
    q_lines.append("</QUESTIONS>")
    return "\n".join(meta_lines + q_lines) + "\n"


@dataclass
class _RunState:
    event_index: int = 0
    reset_count: int = 0
    sut_invocation_count: int = 0
    seen_count_by_qid: dict[str, int] = field(default_factory=dict)


def _next_event_id(idx: int) -> str:
    return f"evt-{idx + 1:04d}"


def run(config: RunConfig) -> Path:
    """Execute the task definition end-to-end. Returns the run directory path."""
    task = config.task
    run_id = config.run_id or _gen_run_id(task.task_id)
    run_root = (config.runs_root / run_id).resolve()
    run_root.mkdir(parents=True, exist_ok=False)

    dir_path = dir_lifecycle.create_dir(run_root)
    dirs = trace_writer.RunDirs.create(run_root)
    state = _RunState()
    started_at = _iso_now()
    started_perf = time.perf_counter()

    stderr_log = run_root / "sut-stderr.log"
    handle = sut_process.spawn_sut(
        config.sut_command,
        dir_path=dir_path,
        invocation_index=state.sut_invocation_count,
        stderr_log=stderr_log,
        extra_pythonpath=config.sut_pythonpath,
    )
    state.sut_invocation_count += 1

    exit_status = "ok"
    sut_manifest_written = False

    try:
        with trace_writer.TraceWriter(dirs) as tw:
            # M4: SUT manifest is read by the CLI from the SUT package dir and
            # passed in config; harness writes it directly to the run root.
            if config.sut_manifest is not None:
                tw.write_sut_manifest(config.sut_manifest)
                sut_manifest_written = True

            for ev in task.events:
                event_id = _next_event_id(state.event_index)

                if ev.type == "read":
                    _run_read(tw, handle, event_id, state, ev, task, config)
                elif ev.type == "quiz":
                    _run_quiz(tw, handle, event_id, state, ev, task, config)
                elif ev.type == "reset":
                    handle = _run_reset(
                        tw, handle, event_id, state, dir_path, dirs, config, stderr_log
                    )
                state.event_index += 1

            # Graceful shutdown of the SUT at end of run.
            sut_process.shutdown_sut(handle)

            ended_at = _iso_now()
            wall_ms = _ms_between(started_perf, time.perf_counter())
            final_bytes, final_files = dir_lifecycle.account_dir(dir_path)

            manifest = {
                "run_id": run_id,
                "task_id": task.task_id,
                "task_path": str(task.source_path),
                "harness_version": HARNESS_VERSION,
                "harness_commit": config.harness_commit,
                "started_at": started_at,
                "ended_at": ended_at,
                "wall_clock_ms": wall_ms,
                "event_count": state.event_index,
                "reset_count": state.reset_count,
                "sut_invocation_count": state.sut_invocation_count,
                "dir_final_uncompressed_bytes": final_bytes,
                "dir_final_file_count": final_files,
                "exit_status": exit_status,
            }
            tw.write_run_manifest(manifest)

            if not sut_manifest_written:
                tw.write_sut_manifest({
                    "name": "unknown",
                    "version": "0.0.0",
                    "mode": "in-context",
                    "hardware_tier": "API",
                    "strict_verbatim": True,
                    "resource_appendix": {},
                    "_note": "SUT did not emit DIR/.harness/sut-manifest.json; harness wrote a stub.",
                })

    except sut_process.SUTTimeout:
        exit_status = "timeout"
        sut_process.kill_sut(handle)
        raise
    except sut_process.SUTError:
        exit_status = "sut_crash"
        # Best-effort kill + re-raise with run dir info preserved for inspection.
        sut_process.kill_sut(handle)
        raise
    except Exception:
        exit_status = "harness_error"
        sut_process.kill_sut(handle)
        raise
    finally:
        if not config.keep_dir:
            dir_lifecycle.cleanup_dir(dir_path)

    return run_root


def _run_read(
    tw: trace_writer.TraceWriter,
    handle: sut_process.SUTHandle,
    event_id: str,
    state: _RunState,
    ev: Event,
    task: TaskDefinition,
    config: RunConfig,
) -> None:
    material = task.materials[ev.material_id]
    payload_in = _render_read_input(event_id, material.id, material.text)
    t0_iso, t0 = _iso_now(), time.perf_counter()
    stage_input_path, stage_input_bytes = tw.write_stage_input(event_id, payload_in)
    reply = sut_process.send_event(
        handle, event_id, "READ", payload_in, timeout_s=config.event_timeout_s,
    )
    stage_output_path = tw.write_stage_output_json(event_id, reply)
    t1_iso, t1 = _iso_now(), time.perf_counter()
    tw.write_event({
        "event_id": event_id,
        "event_index": state.event_index,
        "event_type": "READ",
        "timestamp_start": t0_iso,
        "timestamp_end": t1_iso,
        "wall_clock_ms": _ms_between(t0, t1),
        "sut_process_id": handle.process_id,
        "material_id": material.id,
        "stage_input_path": stage_input_path,
        "stage_input_bytes": stage_input_bytes,
        "stage_output_path": stage_output_path,
    })


def _run_quiz(
    tw: trace_writer.TraceWriter,
    handle: sut_process.SUTHandle,
    event_id: str,
    state: _RunState,
    ev: Event,
    task: TaskDefinition,
    config: RunConfig,
) -> None:
    questions = [task.questions[qid] for qid in ev.questions]
    material_refs = sorted({q.material_ref for q in questions if q.material_ref})
    payload_in = _render_quiz_input(event_id, ev.probe, ev.k, questions)
    t0_iso, t0 = _iso_now(), time.perf_counter()
    stage_input_path, _ = tw.write_stage_input(event_id, payload_in)
    reply = sut_process.send_event(
        handle, event_id, "QUIZ", payload_in, timeout_s=config.event_timeout_s,
    )
    stage_output_path = tw.write_stage_output_json(event_id, reply)
    t1_iso, t1 = _iso_now(), time.perf_counter()

    tw.write_event({
        "event_id": event_id,
        "event_index": state.event_index,
        "event_type": "QUIZ",
        "timestamp_start": t0_iso,
        "timestamp_end": t1_iso,
        "wall_clock_ms": _ms_between(t0, t1),
        "sut_process_id": handle.process_id,
        "probe_type": ev.probe,
        "k": ev.k,
        "question_ids": list(ev.questions),
        "material_refs": material_refs,
        "stage_input_path": stage_input_path,
        "stage_output_path": stage_output_path,
    })

    # Per-question records: built by structural lookup over the SUT's
    # `answers` list, not by parsing text. The harness no longer knows or
    # cares about answer-tag conventions (M4, 2026-05-20).
    looked_up = trace_writer.lookup_sut_answers(reply.get("answers", []), ev.questions)
    for qid in ev.questions:
        q = task.questions[qid]
        seen_before = state.seen_count_by_qid.get(qid, 0)
        rec = {
            "record_id": f"{event_id}-{qid}",
            "event_id": event_id,
            "question_id": qid,
            "probe_type": ev.probe,
            "k": ev.k,
            "question_text": q.text,
            "gold_answer": q.gold,
            "sut_answer": looked_up[qid]["sut_answer"],
            "question_type": q.type,
            "material_ref": q.material_ref,
            "question_seen_before": seen_before,
            "parsing_status": looked_up[qid]["parsing_status"],
        }
        tw.write_question_record(rec)
        state.seen_count_by_qid[qid] = seen_before + 1


def _run_reset(
    tw: trace_writer.TraceWriter,
    handle: sut_process.SUTHandle,
    event_id: str,
    state: _RunState,
    dir_path: Path,
    dirs: trace_writer.RunDirs,
    config: RunConfig,
    stderr_log: Path,
) -> sut_process.SUTHandle:
    t0_iso, t0 = _iso_now(), time.perf_counter()
    sig_name, exit_code = sut_process.kill_sut(handle)
    snapshot_path = dirs.snapshots / f"reset-{event_id}.tar.gz"
    snap = dir_lifecycle.snapshot_dir(dir_path, snapshot_path)
    new_handle = sut_process.spawn_sut(
        config.sut_command,
        dir_path=dir_path,
        invocation_index=state.sut_invocation_count,
        stderr_log=stderr_log,
    )
    state.sut_invocation_count += 1
    state.reset_count += 1
    t1_iso, t1 = _iso_now(), time.perf_counter()

    rel_snapshot = str(snap.snapshot_path.relative_to(dirs.root))
    tw.write_event({
        "event_id": event_id,
        "event_index": state.event_index,
        "event_type": "RESET",
        "timestamp_start": t0_iso,
        "timestamp_end": t1_iso,
        "wall_clock_ms": _ms_between(t0, t1),
        "sut_process_id": handle.process_id,  # the *killed* SUT's id
        "snapshot_path": rel_snapshot,
        "dir_uncompressed_bytes": snap.uncompressed_bytes,
        "dir_file_count": snap.file_count,
        "dir_tarball_bytes": snap.tarball_bytes,
        "sut_kill_signal": sig_name,
        "sut_exit_code": exit_code,
    })
    return new_handle


