"""DIR lifecycle: create, snapshot, account, cleanup.

Snapshots report both uncompressed bytes + file count and tar.gz size. The
harness reserves the `.harness/` prefix inside DIR for its own bookkeeping
(currently nothing used, but always excluded from storage accounting).
"""

from __future__ import annotations

import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

HARNESS_RESERVED_PREFIX = ".harness"


@dataclass
class SnapshotResult:
    snapshot_path: Path
    uncompressed_bytes: int
    file_count: int
    tarball_bytes: int


def create_dir(parent: Path) -> Path:
    """Create a fresh DIR for a run under `parent`. Returns its absolute path."""
    parent.mkdir(parents=True, exist_ok=True)
    dir_path = parent / "dir"
    if dir_path.exists():
        shutil.rmtree(dir_path)
    dir_path.mkdir()
    (dir_path / HARNESS_RESERVED_PREFIX).mkdir()
    return dir_path.resolve()


def account_dir(dir_path: Path) -> tuple[int, int]:
    """Return (uncompressed_bytes, file_count) of regular files in DIR,
    excluding anything under the reserved `.harness/` prefix."""
    total_bytes = 0
    total_files = 0
    for f in dir_path.rglob("*"):
        if not f.is_file():
            continue
        try:
            rel = f.relative_to(dir_path)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == HARNESS_RESERVED_PREFIX:
            continue
        total_bytes += f.stat().st_size
        total_files += 1
    return total_bytes, total_files


def snapshot_dir(dir_path: Path, snapshot_path: Path) -> SnapshotResult:
    """Create a gzip-compressed tar of `dir_path` (excluding `.harness/`)
    at `snapshot_path`. Returns accounting metadata."""
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    uncompressed_bytes, file_count = account_dir(dir_path)
    with tarfile.open(snapshot_path, "w:gz") as tf:
        for f in sorted(dir_path.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(dir_path)
            if rel.parts and rel.parts[0] == HARNESS_RESERVED_PREFIX:
                continue
            tf.add(f, arcname=str(rel))
    tarball_bytes = snapshot_path.stat().st_size
    return SnapshotResult(
        snapshot_path=snapshot_path,
        uncompressed_bytes=uncompressed_bytes,
        file_count=file_count,
        tarball_bytes=tarball_bytes,
    )


def cleanup_dir(dir_path: Path) -> None:
    """Remove the DIR. Caller controls whether to invoke this (default keep)."""
    if dir_path.exists():
        shutil.rmtree(dir_path)
