"""Survive-dir accounting: what the harness counts as the SUT's persisted state.

One live function, `account_dir`, and the prefix it excludes. The harness reserves
`.harness/` inside the survive-dir for its own bookkeeping (nothing writes there
yet) and never counts it as SUT state, so a future harness artefact cannot inflate
the storage signal.

**The survive-dir is created by `retention_bench.system.SubprocessSystem.__init__`,
not here** — deliberately, and it is worth saying why, because this module used to
export a `create_dir` that looked like the reference implementation of that. It
was not one: it created `<parent>/dir` and `rmtree`'d any existing copy, which is
the opposite of what a retention run needs. The live path takes the survive-dir
path as given and creates it with `exist_ok=True`, because the state surviving the
SIGKILL *is the measurement*. The two never shared creation semantics; they shared
only the reserved prefix, which is now asserted directly against
`HARNESS_RESERVED_PREFIX` (see `tests/test_subprocess_system.py`). `create_dir`,
`snapshot_dir` and `cleanup_dir` were removed in RB-25 — they were residue of the
retired book-track harness with no non-test caller.
"""

from __future__ import annotations

from pathlib import Path

HARNESS_RESERVED_PREFIX = ".harness"


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
