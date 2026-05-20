"""CLI entrypoint: `python -m harness <task.yaml> --sut '<cmd>'`."""

from __future__ import annotations

import argparse
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
        help="Shell command to spawn the SUT. Defaults to the built-in stub "
             "(python -m harness.stubs.echo_sut).",
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    task = task_loader.load_task(args.task)

    if args.sut:
        sut_cmd = sut_process.parse_command(args.sut)
    else:
        sut_cmd = [sys.executable, "-m", "harness.stubs.echo_sut"]

    runs_root = Path(args.runs_dir).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    config = event_loop.RunConfig(
        task=task,
        sut_command=sut_cmd,
        runs_root=runs_root,
        run_id=args.run_id,
        harness_commit=_git_commit(repo_root),
        keep_dir=not args.cleanup_dir,
    )
    run_dir = event_loop.run(config)
    print(str(run_dir))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
