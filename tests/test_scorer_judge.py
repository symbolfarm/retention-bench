"""Tests for the LLM-as-judge scorer integration.

All tests are deterministic and offline — no live API calls. The fake
OpenAI shim (tests/fake_openai_shim/openai.py) is injected via
PYTHONPATH and FAKE_OPENAI_FIXTURE env vars.

Coverage:
- Dispatch logic: surface_factual → exact-match, entity_tracking → judge,
  multi_hop → judge, unknown → hard error.
- Judge rationale persistence to scoring.jsonl.
- --scorer exact-match (default) reproduces M6 behavior (q3 stays excluded).
- --scorer judge: q3 "the police" flip — entity_tracking false-negative now
  contributes to the curve.
- q4 surface_factual stays exact-match regardless of --scorer judge (by
  design; gold "a heartbeat" is too terse, flagged as follow-up task).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIM_DIR = REPO_ROOT / "tests" / "fake_openai_shim"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


def _rec(
    qid: str,
    probe: str,
    sut: str,
    gold: str,
    question_type: str = "surface_factual",
    k: int | None = None,
    record_id: str | None = None,
) -> dict:
    return {
        "record_id": record_id or f"evt-{qid}-{probe}",
        "event_id": f"evt-{probe}",
        "question_id": qid,
        "probe_type": probe,
        "k": k,
        "question_text": "Who came to investigate the narrator?",
        "gold_answer": gold,
        "sut_answer": sut,
        "question_type": question_type,
        "material_ref": "m1",
        "question_seen_before": 0,
        "parsing_status": "ok",
    }


def _write_records(run_dir: Path, records: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "questions.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _run_scorer(
    run_dir: Path,
    scorer: str = "exact-match",
    fake_fixture: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = "fake-key-for-tests"
    if fake_fixture is not None:
        env["FAKE_OPENAI_FIXTURE"] = str(fake_fixture)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".counter", delete=False
        ) as cf:
            cf.write("0")
            counter_path = cf.name
        env["FAKE_OPENAI_COUNTER"] = counter_path
        # Inject shim: prepend shim dir to PYTHONPATH so `import openai`
        # resolves to the fake.
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(SHIM_DIR) + (":" + existing if existing else "")

    return subprocess.run(
        [sys.executable, "-m", "scorer", str(run_dir), "--scorer", scorer],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


# ---------------------------------------------------------------------------
# Dispatch unit tests (no subprocess — import the protocol directly)
# ---------------------------------------------------------------------------


def test_dispatch_surface_factual_uses_exact_match():
    from scorer.protocols import ExactMatchScorer, get_scorer
    scorer = get_scorer("surface_factual", scorer_mode="exact-match")
    assert isinstance(scorer, ExactMatchScorer)


def test_dispatch_surface_factual_always_exact_match_even_in_judge_mode():
    """surface_factual bypasses judge regardless of scorer_mode — locked design."""
    from scorer.protocols import ExactMatchScorer, get_scorer
    scorer = get_scorer("surface_factual", scorer_mode="judge")
    assert isinstance(scorer, ExactMatchScorer)


def test_dispatch_entity_tracking_exact_match_mode_uses_exact_match():
    from scorer.protocols import ExactMatchScorer, get_scorer
    scorer = get_scorer("entity_tracking", scorer_mode="exact-match")
    assert isinstance(scorer, ExactMatchScorer)


def test_dispatch_entity_tracking_judge_mode_uses_judge(monkeypatch, tmp_path):
    """entity_tracking with scorer_mode='judge' returns a JudgeScorer instance."""
    from scorer import protocols
    from scorer.judge import JudgeScorer

    # Inject a fresh state so previous tests don't leak singleton.
    protocols.reset_judge_singleton()

    # Provide a fake API key and PYTHONPATH so JudgeScorer can be constructed.
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    # Prepend shim dir so `import openai` resolves to the fake.
    orig = sys.path[:]
    sys.path.insert(0, str(SHIM_DIR))
    # Also set FAKE_OPENAI_FIXTURE so shim doesn't raise on import.
    fixture = FIXTURE_DIR / "fake_judge_responses.yaml"
    monkeypatch.setenv("FAKE_OPENAI_FIXTURE", str(fixture))
    counter_file = tmp_path / "counter.txt"
    counter_file.write_text("0")
    monkeypatch.setenv("FAKE_OPENAI_COUNTER", str(counter_file))
    try:
        protocols.reset_judge_singleton()
        scorer = protocols.get_scorer("entity_tracking", scorer_mode="judge")
        assert isinstance(scorer, JudgeScorer)
    finally:
        sys.path[:] = orig
        protocols.reset_judge_singleton()


def test_dispatch_multi_hop_exact_match_mode_uses_exact_match():
    from scorer.protocols import ExactMatchScorer, get_scorer
    scorer = get_scorer("multi_hop", scorer_mode="exact-match")
    assert isinstance(scorer, ExactMatchScorer)


def test_dispatch_unknown_type_raises_hard_error():
    from scorer.protocols import get_scorer
    with pytest.raises(ValueError, match="Unknown question_type"):
        get_scorer("thematic_open_ended", scorer_mode="exact-match")


def test_dispatch_unknown_type_judge_mode_also_raises():
    from scorer.protocols import get_scorer
    with pytest.raises(ValueError, match="Unknown question_type"):
        get_scorer("mystery_type", scorer_mode="judge")


# ---------------------------------------------------------------------------
# ExactMatchScorer unit tests (via protocols)
# ---------------------------------------------------------------------------


def test_exact_match_scorer_scores_correctly():
    from scorer.protocols import ExactMatchScorer
    s = ExactMatchScorer()
    score, kind, rationale = s.score(
        {"sut_answer": "the police", "gold_answer": "the police", "parsing_status": "ok"}
    )
    assert score == 1.0
    assert kind == "exact_match"
    assert rationale is None


def test_exact_match_scorer_false_negative_on_paraphrase():
    """This is the q3 scenario under exact-match — confirms the limitation."""
    from scorer.protocols import ExactMatchScorer
    s = ExactMatchScorer()
    score, kind, _ = s.score(
        {
            "sut_answer": "Three police officers",
            "gold_answer": "the police",
            "parsing_status": "ok",
        }
    )
    assert score == 0.0
    assert kind == "exact_match"


def test_exact_match_scorer_not_found_scores_zero():
    from scorer.protocols import ExactMatchScorer
    s = ExactMatchScorer()
    score, kind, _ = s.score(
        {
            "sut_answer": "the police",
            "gold_answer": "the police",
            "parsing_status": "not_found",
        }
    )
    assert score == 0.0
    assert kind == "exact_match"


# ---------------------------------------------------------------------------
# --scorer exact-match (default): M6 backward-compat regression
#
# q3 is entity_tracking but scorer_mode=exact-match → exact-match used →
# "Three police officers" != "the police" → score=0 → excluded from curve
# (because C≈P with P=0, C=0 under exact-match).
# ---------------------------------------------------------------------------


def test_exact_match_mode_reproduces_m6_q3_excluded(tmp_path):
    """Under --scorer exact-match, q3 entity_tracking stays excluded (M6 behavior)."""
    run_dir = tmp_path / "run-exact"
    # q3: entity_tracking — under exact-match, "Three police officers" != "the police"
    records = [
        _rec("q3", "prior", "Unknown", "the police", question_type="entity_tracking"),
        _rec("q3", "ceiling", "Three police officers", "the police",
             question_type="entity_tracking"),
        _rec("q3", "retention", "Three police officers", "the police",
             question_type="entity_tracking", k=1),
    ]
    _write_records(run_dir, records)
    result = _run_scorer(run_dir, scorer="exact-match")
    assert result.returncode == 0, result.stderr
    # C=0 (exact-match fails), P=0 → C-P=0 < ε → excluded
    assert "excluded" in result.stdout
    # No scoring.jsonl in exact-match mode
    assert not (run_dir / "scoring.jsonl").exists()


# ---------------------------------------------------------------------------
# --scorer judge: q3 flip test (the key acceptance criterion)
#
# Uses the fake OpenAI shim with canned tool-call responses.
# q3 entity_tracking: judge scores ceiling=1, retention=1 → contributes to curve.
# ---------------------------------------------------------------------------


def test_judge_mode_q3_flip(tmp_path):
    """Under --scorer judge, the entity_tracking q3 false-negative flips to 1.

    Demonstrates: P=0 (prior Unknown→0), C=1 (judge scores 'Three police
    officers' as equivalent to 'the police'), R(1)=1 → norm R = 1.0.
    Question now contributes to the curve rather than being excluded.
    """
    run_dir = tmp_path / "run-judge"
    records = [
        _rec("q3", "prior", "Unknown", "the police",
             question_type="entity_tracking",
             record_id="rec-q3-prior"),
        _rec("q3", "ceiling", "Three police officers", "the police",
             question_type="entity_tracking",
             record_id="rec-q3-ceiling"),
        _rec("q3", "retention", "Three police officers", "the police",
             question_type="entity_tracking",
             k=1, record_id="rec-q3-retention"),
    ]
    _write_records(run_dir, records)

    fixture = FIXTURE_DIR / "fake_judge_responses.yaml"
    result = _run_scorer(run_dir, scorer="judge", fake_fixture=fixture)
    assert result.returncode == 0, result.stderr

    # q3 should NOT be excluded — it has C=1, P=0, gap=1 ≥ ε
    assert "excluded" not in result.stdout
    # norm R at k=1 should be 1.00
    assert "1.00" in result.stdout
    # Aggregate should show n_usable=1
    assert "n_usable=1" in result.stdout


def test_judge_mode_scoring_jsonl_written(tmp_path):
    """Under --scorer judge, rationales are persisted to scoring.jsonl."""
    run_dir = tmp_path / "run-judge-jsonl"
    records = [
        _rec("q3", "prior", "Unknown", "the police",
             question_type="entity_tracking",
             record_id="rec-q3-prior"),
        _rec("q3", "ceiling", "Three police officers", "the police",
             question_type="entity_tracking",
             record_id="rec-q3-ceiling"),
        _rec("q3", "retention", "Three police officers", "the police",
             question_type="entity_tracking",
             k=1, record_id="rec-q3-retention"),
    ]
    _write_records(run_dir, records)

    fixture = FIXTURE_DIR / "fake_judge_responses.yaml"
    result = _run_scorer(run_dir, scorer="judge", fake_fixture=fixture)
    assert result.returncode == 0, result.stderr

    scoring_path = run_dir / "scoring.jsonl"
    assert scoring_path.exists(), "scoring.jsonl not written"

    entries = [json.loads(line) for line in scoring_path.read_text().splitlines() if line.strip()]
    assert len(entries) == 3, f"Expected 3 judge rationale entries, got {len(entries)}"

    record_ids = {e["record_id"] for e in entries}
    assert "rec-q3-prior" in record_ids
    assert "rec-q3-ceiling" in record_ids
    assert "rec-q3-retention" in record_ids

    # All entries have rationale and scorer_kind
    for e in entries:
        assert e["scorer_kind"] == "judge"
        assert "judge_rationale" in e
        assert len(e["judge_rationale"]) > 0


def test_judge_mode_scoring_jsonl_keyed_by_record_id(tmp_path):
    """scoring.jsonl entries include record_id for auditability."""
    run_dir = tmp_path / "run-judge-keyed"
    records = [
        _rec("q3", "ceiling", "Three police officers", "the police",
             question_type="entity_tracking",
             record_id="my-custom-record-id"),
    ]
    _write_records(run_dir, records)

    # Only need one fixture response for one judge call
    single_response_fixture = tmp_path / "single.yaml"
    single_response_fixture.write_text(
        "responses:\n"
        "  - tool_use:\n"
        "      name: judge_verdict\n"
        "      input:\n"
        "        rationale: Semantically equivalent.\n"
        "        score: 1\n"
        "    input_tokens: 100\n"
        "    output_tokens: 30\n"
    )

    result = _run_scorer(run_dir, scorer="judge", fake_fixture=single_response_fixture)
    assert result.returncode == 0, result.stderr

    scoring_path = run_dir / "scoring.jsonl"
    entries = [json.loads(line) for line in scoring_path.read_text().splitlines() if line.strip()]
    assert entries[0]["record_id"] == "my-custom-record-id"


# ---------------------------------------------------------------------------
# q4 surface_factual: stays exact-match regardless of --scorer judge
#
# q4 ("a heartbeat") is surface_factual — exact-match by locked dispatch.
# The SUT answered "The old man's heartbeat" → exact-match fails → C=0.
# This is BY DESIGN: the scorer does not paraphrase-rescue surface_factual.
# These hand-built records reproduce the original false-negative to lock that
# behaviour; the *smoke asset itself* was since fixed in B12 (q4 tightened to
# a single-word "heartbeat" gold), which is an asset fix, not a scorer fix.
# ---------------------------------------------------------------------------


def test_q4_surface_factual_stays_exact_match_under_judge_mode(tmp_path):
    """q4 surface_factual is NOT routed to judge, even with --scorer judge."""
    run_dir = tmp_path / "run-q4"
    # q4: surface_factual — even with --scorer judge, must use exact-match
    records = [
        _rec("q4", "prior", "Unknown", "a heartbeat",
             question_type="surface_factual"),
        _rec("q4", "ceiling", "The old man's heartbeat", "a heartbeat",
             question_type="surface_factual"),
        _rec("q4", "retention", "The old man's heartbeat", "a heartbeat",
             question_type="surface_factual", k=1),
    ]
    _write_records(run_dir, records)

    # No fixture needed — no judge calls should be made for surface_factual.
    # We pass a fake fixture with 0 responses to confirm no calls happen.
    empty_fixture = tmp_path / "empty.yaml"
    empty_fixture.write_text("responses: []\n")

    result = _run_scorer(run_dir, scorer="judge", fake_fixture=empty_fixture)
    assert result.returncode == 0, result.stderr
    # "The old man's heartbeat" != "a heartbeat" under exact-match → C=0, excluded
    assert "excluded" in result.stdout


# ---------------------------------------------------------------------------
# Mixed: surface_factual + entity_tracking together under judge mode
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# B11: judge_resource_appendix accumulation
#
# Judge token usage is accumulated across the run and written to a sibling
# judge_resource_appendix.jsonl, distinct from the SUT's resource_appendix.
# ---------------------------------------------------------------------------


def test_judge_resource_appendix_accumulates(tmp_path):
    """Judge mode writes judge_resource_appendix.jsonl with accumulated usage.

    The shared fake fixture has three judge calls:
      120+45, 130+50, 130+50  →  input=380, output=145, api_call_count=3.
    """
    run_dir = tmp_path / "run-appendix"
    records = [
        _rec("q3", "prior", "Unknown", "the police",
             question_type="entity_tracking", record_id="rec-q3-prior"),
        _rec("q3", "ceiling", "Three police officers", "the police",
             question_type="entity_tracking", record_id="rec-q3-ceiling"),
        _rec("q3", "retention", "Three police officers", "the police",
             question_type="entity_tracking", k=1, record_id="rec-q3-retention"),
    ]
    _write_records(run_dir, records)

    fixture = FIXTURE_DIR / "fake_judge_responses.yaml"
    result = _run_scorer(run_dir, scorer="judge", fake_fixture=fixture)
    assert result.returncode == 0, result.stderr

    appendix_path = run_dir / "judge_resource_appendix.jsonl"
    assert appendix_path.exists(), "judge_resource_appendix.jsonl not written"

    lines = [l for l in appendix_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 1, "expected a single aggregate appendix record"
    appendix = json.loads(lines[0])

    assert appendix["kind"] == "api"
    assert appendix["api_call_count"] == 3
    assert appendix["input_tokens"] == 380
    assert appendix["output_tokens"] == 145
    assert appendix["model_id"]  # non-empty resolved model id


def test_no_judge_appendix_in_exact_match_mode(tmp_path):
    """exact-match mode never writes a judge_resource_appendix."""
    run_dir = tmp_path / "run-exact-no-appendix"
    records = [
        _rec("q1", "prior", "wrong", "right", question_type="surface_factual"),
        _rec("q1", "ceiling", "right", "right", question_type="surface_factual"),
        _rec("q1", "retention", "right", "right",
             question_type="surface_factual", k=1),
    ]
    _write_records(run_dir, records)
    result = _run_scorer(run_dir, scorer="exact-match")
    assert result.returncode == 0, result.stderr
    assert not (run_dir / "judge_resource_appendix.jsonl").exists()


def test_no_judge_appendix_when_judge_never_engaged(tmp_path):
    """Judge mode with only surface_factual records writes no appendix.

    surface_factual bypasses the judge, so the judge singleton is never
    instantiated and there is no spend to report.
    """
    run_dir = tmp_path / "run-judge-surface-only"
    records = [
        _rec("q4", "prior", "Unknown", "a heartbeat",
             question_type="surface_factual"),
        _rec("q4", "ceiling", "The old man's heartbeat", "a heartbeat",
             question_type="surface_factual"),
    ]
    _write_records(run_dir, records)
    empty_fixture = tmp_path / "empty.yaml"
    empty_fixture.write_text("responses: []\n")
    result = _run_scorer(run_dir, scorer="judge", fake_fixture=empty_fixture)
    assert result.returncode == 0, result.stderr
    assert not (run_dir / "judge_resource_appendix.jsonl").exists()


def test_judge_mode_mixed_types(tmp_path):
    """surface_factual stays exact-match; entity_tracking gets judge."""
    run_dir = tmp_path / "run-mixed"

    records = [
        # q1: surface_factual — exact-match, clear hit
        _rec("q1", "prior", "wrong", "right", question_type="surface_factual"),
        _rec("q1", "ceiling", "right", "right", question_type="surface_factual"),
        _rec("q1", "retention", "right", "right",
             question_type="surface_factual", k=1),
        # q3: entity_tracking — goes to judge
        _rec("q3", "prior", "Unknown", "the police",
             question_type="entity_tracking",
             record_id="rec-q3-prior-mixed"),
        _rec("q3", "ceiling", "Three police officers", "the police",
             question_type="entity_tracking",
             record_id="rec-q3-ceiling-mixed"),
        _rec("q3", "retention", "Three police officers", "the police",
             question_type="entity_tracking",
             k=1, record_id="rec-q3-retention-mixed"),
    ]
    _write_records(run_dir, records)

    fixture = FIXTURE_DIR / "fake_judge_responses.yaml"
    result = _run_scorer(run_dir, scorer="judge", fake_fixture=fixture)
    assert result.returncode == 0, result.stderr

    # Both q1 (exact-match) and q3 (judge, now scoring 1) contribute
    assert "n_usable=2" in result.stdout

    # scoring.jsonl should only contain q3 entries (entity_tracking)
    scoring_path = run_dir / "scoring.jsonl"
    entries = [json.loads(line) for line in scoring_path.read_text().splitlines() if line.strip()]
    assert len(entries) == 3  # q3's prior, ceiling, retention
    question_ids = {e["question_id"] for e in entries}
    assert question_ids == {"q3"}
    # q1 should NOT appear in scoring.jsonl (exact-match, no rationale)
    assert "q1" not in question_ids
