"""Tests for DIR snapshot accounting (bytes + file count + tarball)."""

from __future__ import annotations

import tarfile
from pathlib import Path

from harness import dir_lifecycle


def _write(p: Path, content: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def test_account_dir_excludes_harness_prefix(tmp_path: Path) -> None:
    d = dir_lifecycle.create_dir(tmp_path / "run")
    _write(d / "a.txt", b"hello")          # 5 bytes
    _write(d / "sub" / "b.bin", b"xyz")    # 3 bytes
    _write(d / ".harness" / "bookkeep", b"ignored-by-accounting")
    nbytes, nfiles = dir_lifecycle.account_dir(d)
    assert nbytes == 8
    assert nfiles == 2


def test_snapshot_dir_produces_tarball_and_correct_accounting(tmp_path: Path) -> None:
    d = dir_lifecycle.create_dir(tmp_path / "run")
    _write(d / "a.txt", b"a" * 100)
    _write(d / "nested" / "b.txt", b"b" * 200)
    _write(d / ".harness" / "skip.txt", b"SHOULD NOT APPEAR")
    snap_path = tmp_path / "snap.tar.gz"
    result = dir_lifecycle.snapshot_dir(d, snap_path)

    assert result.uncompressed_bytes == 300
    assert result.file_count == 2
    assert snap_path.is_file()
    assert result.tarball_bytes == snap_path.stat().st_size
    assert result.tarball_bytes > 0

    with tarfile.open(snap_path, "r:gz") as tf:
        names = sorted(tf.getnames())
    assert names == ["a.txt", "nested/b.txt"]
    assert all(not n.startswith(".harness") for n in names)


def test_snapshot_empty_dir_is_valid(tmp_path: Path) -> None:
    d = dir_lifecycle.create_dir(tmp_path / "run")
    snap_path = tmp_path / "snap.tar.gz"
    result = dir_lifecycle.snapshot_dir(d, snap_path)
    assert result.uncompressed_bytes == 0
    assert result.file_count == 0
    assert snap_path.is_file()
