"""Tests for survive-dir accounting — the bytes/file-count signal the harness reports.

RB-25 removed this module's `create_dir`/`snapshot_dir`/`cleanup_dir`, so these
tests build the survive-dir the way a real run does (a plain `mkdir` plus the
reserved prefix) rather than through a helper no production code called.
"""

from __future__ import annotations

from pathlib import Path

from harness import dir_lifecycle


def _make_dir(parent: Path) -> Path:
    """A survive-dir as `SubprocessSystem.__init__` makes one."""
    parent.mkdir(parents=True, exist_ok=True)
    (parent / dir_lifecycle.HARNESS_RESERVED_PREFIX).mkdir(exist_ok=True)
    return parent


def _write(p: Path, content: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def test_account_dir_excludes_harness_prefix(tmp_path: Path) -> None:
    d = _make_dir(tmp_path / "run")
    _write(d / "a.txt", b"hello")          # 5 bytes
    _write(d / "sub" / "b.bin", b"xyz")    # 3 bytes
    _write(d / ".harness" / "bookkeep", b"ignored-by-accounting")
    nbytes, nfiles = dir_lifecycle.account_dir(d)
    assert nbytes == 8
    assert nfiles == 2


def test_account_dir_counts_nested_files(tmp_path: Path) -> None:
    d = _make_dir(tmp_path / "run")
    _write(d / "a.txt", b"a" * 100)
    _write(d / "nested" / "b.txt", b"b" * 200)
    _write(d / ".harness" / "skip.txt", b"SHOULD NOT BE COUNTED")
    assert dir_lifecycle.account_dir(d) == (300, 2)


def test_account_empty_dir_is_zero(tmp_path: Path) -> None:
    """An empty survive-dir accounts as zero even though `.harness/` exists —
    the reserved prefix must never make a stateless arm look like it retained."""
    d = _make_dir(tmp_path / "run")
    assert dir_lifecycle.account_dir(d) == (0, 0)
