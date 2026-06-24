"""C10: the BSM ``mixed_grid_lifecycle`` frozen corpus is reproducible.

The ``default`` three-stage schedule requires this corpus on disk (CL-Bench
raises ``FileNotFoundError`` otherwise). It ships git-tracked inside the
cl-benchmark dependency; this test pins the *reproducibility* contract — the
seeded DGP rollout regenerates the committed bytes exactly — so a drift in
CL-Bench's DGP, variant defaults, or schedule seeds is caught here rather than
silently changing the corpus under the drift-placement experiment.

Regenerates into a temp dir only; never mutates the canonical data dir.

Requires the ``cl-benchmark`` distribution (import ``src``, Python >=3.13).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

from retention_bench.bsm_corpus import (  # noqa: E402
    EXPECTED_SHA256,
    ROLLOUT_SCHEDULE_ID,
    corpus_paths,
    materialize_to,
    verify_corpus,
)


def test_regenerates_committed_bytes_exactly():
    """A fresh seeded rollout reproduces the committed sha256 byte-for-byte."""
    tmp = Path(tempfile.mkdtemp(prefix="bsm-corpus-test-"))
    sha = materialize_to(tmp / "c.jsonl", tmp / "c_metadata.json")
    assert sha == EXPECTED_SHA256


def test_on_disk_corpus_matches_regeneration():
    """The corpus shipped in the cl-bench data dir is the reproducible artifact
    (so the default schedule runs against exactly what we can regenerate)."""
    jsonl_path, metadata_path = corpus_paths()
    assert jsonl_path.exists(), f"frozen corpus missing at {jsonl_path}"
    assert metadata_path.exists(), f"corpus metadata missing at {metadata_path}"
    ok, regen_sha, on_disk_sha = verify_corpus()
    assert on_disk_sha == EXPECTED_SHA256
    assert regen_sha == on_disk_sha
    assert ok


def test_default_schedule_constructs_without_filenotfound():
    """The whole point: with the corpus present the 3-stage default schedule
    constructs (no FileNotFoundError) and exposes the 90-instance / drift-at-30,60
    structure the placement experiment relies on."""
    from retention_bench._clbench import get_task_class

    task = get_task_class("blind_spectrum_monitoring")(
        schedule=ROLLOUT_SCHEDULE_ID, probe_mode=True
    )
    assert task.num_instances == 90
    # Corpus stage boundaries are the drift points (completed-instance ordinals).
    stages = task._frozen_corpus_metadata.stages
    assert [s.end_scan_idx for s in stages] == [30, 60, 90]
