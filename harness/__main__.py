"""CLI entrypoint: `python -m harness <task.yaml> --sut <path-to-sut-pkg>`.

The SUT package directory must contain a `sut-manifest.json` declaring an
`entrypoint` argv array. The harness reads the manifest, copies it into the
run directory, and launches the entrypoint with cwd=DIR.

A `--sut-cmd` shortcut is retained for the built-in stubs used in tests.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import event_loop, sut_process, task_loader


def _git_commit(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=2,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m harness",
        description="Run a retention-bench task definition against a SUT subprocess.",
    )
    p.add_argument("task", help="Path to a task-definition YAML file.")
    p.add_argument(
        "--sut",
        default=None,
        help="Path to a SUT package directory containing sut-manifest.json.",
    )
    p.add_argument(
        "--sut-cmd",
        default=None,
        help="(Test shortcut.) Raw shell command to spawn a SUT instead of "
             "loading a manifest. Use --sut for real SUTs.",
    )
    p.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory under which to create the run directory. Default: ./runs",
    )
    p.add_argument(
        "--run-id",
        default=None,
        help="Override the auto-generated run_id (must be unique under --runs-dir).",
    )
    p.add_argument(
        "--cleanup-dir",
        action="store_true",
        help="Delete the run's DIR after the run completes (default: keep for inspection).",
    )
    p.add_argument(
        "--event-timeout",
        type=float,
        default=None,
        help="Override the per-event timeout in seconds (default: 300, or the "
             "task definition's event_timeout_seconds if set).",
    )
    return p


def _load_sut(sut_dir: str | None, sut_cmd: str | None) -> tuple[list[str], dict | None]:
    """Resolve (entrypoint argv, sut_manifest dict) from CLI flags.

    Precedence: --sut (manifest dir) > --sut-cmd (raw command) > built-in stub.
    """
    if sut_dir:
        path = Path(sut_dir).resolve()
        manifest_path = path / "sut-manifest.json"
        if not manifest_path.is_file():
            raise SystemExit(f"--sut: no sut-manifest.json under {path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entrypoint = manifest.get("entrypoint")
        if not isinstance(entrypoint, list) or not entrypoint:
            raise SystemExit(
                f"sut-manifest.json missing or invalid 'entrypoint' array: {manifest_path}"
            )
        return [str(x) for x in entrypoint], manifest
    if sut_cmd:
        return sut_process.parse_command(sut_cmd), None
    # Built-in stub for harness-only smoke tests.
    return [sys.executable, "-m", "harness.stubs.echo_sut"], None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    task = task_loader.load_task(args.task)
    sut_cmd, sut_manifest = _load_sut(args.sut, args.sut_cmd)

    # When --sut <pkg-dir> is used, add the pkg dir to the spawned SUT's
    # PYTHONPATH so `python -m <module>` entrypoints resolve from cwd=DIR.
    sut_pythonpath: list[Path] = []
    if args.sut:
        sut_pythonpath.append(Path(args.sut).resolve())

    runs_root = Path(args.runs_dir).resolve()
    repo_root = Path(__file__).resolve().parent.parent

    # Timeout precedence: CLI flag > task definition > default (300s).
    if args.event_timeout is not None:
        event_timeout_s = args.event_timeout
    elif getattr(task, "event_timeout_seconds", None) is not None:
        event_timeout_s = float(task.event_timeout_seconds)
    else:
        event_timeout_s = 300.0

    config = event_loop.RunConfig(
        task=task,
        sut_command=sut_cmd,
        runs_root=runs_root,
        run_id=args.run_id,
        harness_commit=_git_commit(repo_root),
        keep_dir=not args.cleanup_dir,
        event_timeout_s=event_timeout_s,
        sut_manifest=sut_manifest,
        sut_pythonpath=sut_pythonpath,
    )
    run_dir = event_loop.run(config)
    print(str(run_dir))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
