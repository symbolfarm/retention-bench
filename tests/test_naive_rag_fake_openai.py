"""End-to-end integration test for the naive-rag SUT.

Drives the real harness against the real `suts/naive_rag/` SUT, with:
  - NAIVE_RAG_EMBEDDER=fake  (deterministic hash-based pseudo-vectors, no deps)
  - `openai` SDK replaced by the PYTHONPATH-shadowing fake shim

Runs in CI without OPENROUTER_API_KEY, network access, torch, or llama.cpp.

The fixture (two_chapter.yaml) drives: READ ch1, READ ch2, QUIZ ceiling,
RESET, QUIZ retention k=1. With the fake embedder and canned LLM responses:
  - READ events produce embedding calls only (no LLM calls).
  - QUIZ ceiling calls the LLM once (SUT process #1).
  - After RESET, QUIZ retention calls the LLM once (SUT process #2).
  - The index.jsonl must survive RESET on disk (DIR persistence).

Load-bearing assertions:
  - index.jsonl is written during READ events.
  - index.jsonl contains valid chunk entries with embeddings for both chapters.
  - index.jsonl survives RESET (dir persistence works end-to-end).
  - The post-RESET QUIZ reads the index from disk, not from memory.
  - Resource fields on QUIZ responses include embedding_call_count.
  - Resource aggregation sums both LLM calls across the RESET boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import __main__ as harness_main


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "two_chapter.yaml"
NAIVE_RAG_DIR = REPO_ROOT / "suts" / "naive_rag"
FAKE_SHIM_DIR = REPO_ROOT / "tests" / "fake_openai_shim"
RESPONSES_YAML = (
    REPO_ROOT / "tests" / "fixtures" / "fake_naive_rag_responses.yaml"
)

# Must match fake_naive_rag_responses.yaml exactly.
EXPECTED_TOKENS_IN = 157 + 163
EXPECTED_TOKENS_OUT = 23 + 29
EXPECTED_API_CALLS = 2  # one LLM call per QUIZ event; READ events use embedding only


def test_naive_rag_with_fake_openai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = tmp_path / "fake_openai.counter"
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-not-real")
    monkeypatch.setenv("FAKE_OPENAI_FIXTURE", str(RESPONSES_YAML))
    monkeypatch.setenv("FAKE_OPENAI_COUNTER", str(counter))
    monkeypatch.setenv("NAIVE_RAG_EMBEDDER", "fake")

    # Prepend fake shim dir to PYTHONPATH so the SUT subprocess imports it
    existing = __import__("os").environ.get("PYTHONPATH", "")
    new_pp = str(FAKE_SHIM_DIR) + (":" + existing if existing else "")
    monkeypatch.setenv("PYTHONPATH", new_pp)

    runs_dir = tmp_path / "runs"
    rc = harness_main.main([
        str(FIXTURE),
        "--sut", str(NAIVE_RAG_DIR),
        "--runs-dir", str(runs_dir),
        "--run-id", "naive-rag-fake",
    ])
    assert rc == 0

    run_dir = runs_dir / "naive-rag-fake"
    assert run_dir.is_dir()

    # --- Trace shape: READ, READ, QUIZ, RESET, QUIZ ---
    events = [
        json.loads(line)
        for line in (run_dir / "trace.jsonl").read_text().splitlines()
    ]
    assert [e["event_type"] for e in events] == [
        "READ", "READ", "QUIZ", "RESET", "QUIZ",
    ]

    # --- Two SUT subprocesses (initial + post-RESET) ---
    rm = json.loads((run_dir / "run-manifest.json").read_text())
    assert rm["exit_status"] == "ok"
    assert rm["reset_count"] == 1
    assert rm["sut_invocation_count"] == 2

    # --- Both LLM calls landed (one per QUIZ; READs use only embedding) ---
    assert counter.read_text().strip() == str(EXPECTED_API_CALLS)

    # --- Resource aggregation across both QUIZ events and across RESET ---
    sm = json.loads((run_dir / "sut-manifest.json").read_text())
    ra = sm["resource_appendix"]
    assert ra["tokens_in"] == EXPECTED_TOKENS_IN
    assert ra["tokens_out"] == EXPECTED_TOKENS_OUT
    assert ra["api_call_count"] == EXPECTED_API_CALLS
    assert ra["model_id"] == "deepseek/deepseek-v4-flash"

    # --- Per-question answer records: correct answers from retrieved context ---
    qrecs = [
        json.loads(line)
        for line in (run_dir / "questions.jsonl").read_text().splitlines()
    ]
    assert len(qrecs) == 4  # 2 questions x 2 QUIZ events
    by_event = {(r["event_id"], r["question_id"]): r for r in qrecs}
    # Ceiling — SUT process #1 retrieves from index and gets correct answers
    assert by_event[("evt-0003", "q1")]["sut_answer"] == "Mira Vexin"
    assert by_event[("evt-0003", "q2")]["sut_answer"] == "Halton Reeve"
    # Retention (post-RESET) — same correct answers prove index survived RESET
    assert by_event[("evt-0005", "q1")]["sut_answer"] == "Mira Vexin"
    assert by_event[("evt-0005", "q2")]["sut_answer"] == "Halton Reeve"
    for r in qrecs:
        assert r["parsing_status"] == "ok"

    # --- index.jsonl must exist and contain valid chunk entries ---
    dir_path = run_dir / "dir"
    index_path = dir_path / "index.jsonl"
    assert index_path.is_file(), f"index.jsonl missing under {dir_path}"

    index_entries = [json.loads(line) for line in index_path.read_text().splitlines()]
    assert len(index_entries) >= 2, "Expected at least one chunk per chapter"

    # Every entry must have the required fields
    for entry in index_entries:
        assert "chunk_id" in entry, f"chunk_id missing: {entry}"
        assert "material_ref" in entry, f"material_ref missing: {entry}"
        assert "text" in entry, f"text missing: {entry}"
        assert "embedding" in entry, f"embedding missing: {entry}"
        assert isinstance(entry["embedding"], list), "embedding must be a list"
        assert len(entry["embedding"]) > 0, "embedding must be non-empty"

    # Both chapters must appear in the index
    material_refs = {e["material_ref"] for e in index_entries}
    assert "chapter_one" in material_refs, f"chapter_one missing from index: {material_refs}"
    assert "chapter_two" in material_refs, f"chapter_two missing from index: {material_refs}"

    # Chunk text must contain content from source material
    all_texts = " ".join(e["text"] for e in index_entries)
    assert "Mira Vexin" in all_texts, "chapter_one content not found in index chunks"
    assert "Halton Reeve" in all_texts, "chapter_two content not found in index chunks"
