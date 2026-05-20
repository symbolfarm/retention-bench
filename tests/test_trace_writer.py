"""Tests for trace_writer record shape + SUT-answer parsing."""

from __future__ import annotations

import json
from pathlib import Path

from harness import trace_writer


def test_stage_payload_roundtrip(tmp_path: Path) -> None:
    dirs = trace_writer.RunDirs.create(tmp_path / "run")
    with trace_writer.TraceWriter(dirs) as tw:
        rel_in, n_bytes = tw.write_stage_input("evt-0001", "hello world\n")
        rel_out = tw.write_stage_output("evt-0001", "<ANSWER id=\"q1\">x</ANSWER>")
    assert rel_in == "stages/evt-0001.in"
    assert rel_out == "stages/evt-0001.out"
    assert n_bytes == len(b"hello world\n")
    assert (dirs.root / rel_in).read_bytes() == b"hello world\n"


def test_event_and_question_records_are_jsonl(tmp_path: Path) -> None:
    dirs = trace_writer.RunDirs.create(tmp_path / "run")
    with trace_writer.TraceWriter(dirs) as tw:
        tw.write_event({
            "event_id": "evt-0001",
            "event_index": 0,
            "event_type": "QUIZ",
            "timestamp_start": "2026-05-20T00:00:00.000Z",
            "timestamp_end": "2026-05-20T00:00:00.010Z",
            "wall_clock_ms": 10,
            "sut_process_id": "sut-01",
            "probe_type": "prior",
            "k": None,
            "question_ids": ["q1"],
            "material_refs": [],
            "stage_input_path": "stages/evt-0001.in",
            "stage_output_path": "stages/evt-0001.out",
        })
        tw.write_question_record({
            "record_id": "evt-0001-q1",
            "event_id": "evt-0001",
            "question_id": "q1",
            "probe_type": "prior",
            "k": None,
            "question_text": "?",
            "gold_answer": "x",
            "sut_answer": "y",
            "question_type": "surface_factual",
            "material_ref": None,
            "question_seen_before": 0,
            "parsing_status": "ok",
        })
    trace_lines = (dirs.root / "trace.jsonl").read_text().splitlines()
    q_lines = (dirs.root / "questions.jsonl").read_text().splitlines()
    assert len(trace_lines) == 1 and len(q_lines) == 1
    parsed = json.loads(trace_lines[0])
    # Schema fields required by docs/trace-schema.md for QUIZ events.
    for field in [
        "event_id", "event_index", "event_type", "timestamp_start", "timestamp_end",
        "wall_clock_ms", "sut_process_id", "probe_type", "k", "question_ids",
        "material_refs", "stage_input_path", "stage_output_path",
    ]:
        assert field in parsed, f"missing field {field}"
    qrec = json.loads(q_lines[0])
    for field in [
        "record_id", "event_id", "question_id", "probe_type", "k", "question_text",
        "gold_answer", "sut_answer", "question_type", "material_ref",
        "question_seen_before", "parsing_status",
    ]:
        assert field in qrec, f"missing field {field}"


def test_parse_sut_answers_ok_notfound_ambiguous() -> None:
    out = (
        '<ANSWER id="q1">first</ANSWER>\n'
        '<ANSWER id="q2">second</ANSWER>\n'
        '<ANSWER id="q2">again</ANSWER>\n'
    )
    parsed = trace_writer.parse_sut_answers(out, ["q1", "q2", "q3"])
    assert parsed["q1"] == {"sut_answer": "first", "parsing_status": "ok"}
    assert parsed["q2"] == {"sut_answer": "second", "parsing_status": "ambiguous"}
    assert parsed["q3"] == {"sut_answer": "", "parsing_status": "not_found"}


def test_parse_sut_answers_multiline_body() -> None:
    out = '<ANSWER id="q1">line one\nline two</ANSWER>'
    parsed = trace_writer.parse_sut_answers(out, ["q1"])
    assert parsed["q1"]["parsing_status"] == "ok"
    assert parsed["q1"]["sut_answer"] == "line one\nline two"
