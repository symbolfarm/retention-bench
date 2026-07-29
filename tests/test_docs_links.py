"""Docs must not reference files that don't exist.

Filed with the RB-20 AGENTS.md refresh. AGENTS.md had drifted two pivots out of date and
its read order pointed at ~13 archived or deleted documents; nothing caught it, because a
dangling doc reference breaks nothing at runtime. These tests convert that failure mode
from "noticed months later by a human" into "fails on the commit that causes it".

Two checks, because the observed failure needed both:

* ``test_relative_links_resolve`` — markdown ``[text](target)`` links, across all tracked
  markdown. This is the common case in README/docs.
* ``test_orientation_docs_backticked_paths_resolve`` — backticked paths like
  ``` `docs/foo.md` ```, in the orientation files only. **The stale AGENTS.md contained
  zero markdown links** — every one of its dead references was a backticked path, so the
  link check alone would have passed it. Scoped to the orientation docs because those are
  where path rot misdirects an agent, and because a repo-wide sweep would flag prose that
  names files hypothetically.

Excludes the frozen trees (``docs/archive/``, ``history/``): they are deliberate snapshots
and are expected to reference things that no longer exist.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Frozen/superseded trees: kept for archaeology, not maintained.
EXCLUDED_PREFIXES = ("docs/archive/", "history/")

# [text](target) — skip images (![...]) via the negative lookbehind.
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def _tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [
        REPO_ROOT / p for p in out if not p.startswith(EXCLUDED_PREFIXES)
    ]


def _is_relative(target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    return True


def _resolve(md_file: Path, target: str) -> Path:
    # Strip any fragment/anchor and surrounding whitespace; keep the path part.
    path_part = target.split("#", 1)[0].strip()
    return (md_file.parent / path_part).resolve()


@pytest.mark.parametrize(
    "md_file", _tracked_markdown(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_relative_links_resolve(md_file: Path) -> None:
    broken: list[str] = []
    for target in LINK_RE.findall(md_file.read_text(encoding="utf-8")):
        if not _is_relative(target):
            continue
        path_part = target.split("#", 1)[0].strip()
        if not path_part:  # pure anchor, e.g. [x](#section)
            continue
        if not _resolve(md_file, target).exists():
            broken.append(target)

    assert not broken, (
        f"{md_file.relative_to(REPO_ROOT)} has {len(broken)} dangling relative link(s): "
        + ", ".join(broken)
    )


# The docs whose whole job is pointing an agent at files *in this repo*. Path rot here
# misdirects work, which is exactly what RB-20 was filed for.
#
# TASKS.md is deliberately NOT in this list, despite being the primary orientation doc.
# It carries two legitimate classes of reference to files that do not exist here: the
# "Historical" archaeology sections, which name deleted files precisely in order to say
# they were deleted (`harness/event_loop.py`, `docs/trace-schema.md`, …), and live
# cross-repo citations (constructive-retention debriefs). Both would fire as false
# positives, and a test that cries wolf gets muted — which would be worse than no test.
ORIENTATION_DOCS = ("AGENTS.md", "README.md", "docs/README.md")

# Backticked things that look like a repo-relative path: at least one `/` or a known
# extension, no spaces, not a URL or a shell/env fragment.
BACKTICK_PATH_RE = re.compile(r"`([A-Za-z0-9_.][A-Za-z0-9_./-]*\.(?:md|py|jsonl|sh|toml|json))`")

# Paths named as illustrations rather than as references to real files.
BACKTICK_ALLOWLIST = {
    "/path/to/python",
}


@pytest.mark.parametrize("rel", ORIENTATION_DOCS)
def test_orientation_docs_backticked_paths_resolve(rel: str) -> None:
    md_file = REPO_ROOT / rel
    if not md_file.exists():
        pytest.skip(f"{rel} not present")

    broken: list[str] = []
    for target in BACKTICK_PATH_RE.findall(md_file.read_text(encoding="utf-8")):
        if target in BACKTICK_ALLOWLIST:
            continue
        # Resolve repo-relative first (how orientation docs cite paths), then
        # relative to the citing file.
        if (REPO_ROOT / target).exists() or (md_file.parent / target).exists():
            continue
        broken.append(target)

    assert not broken, (
        f"{rel} cites {len(broken)} path(s) that do not exist: " + ", ".join(broken)
    )
