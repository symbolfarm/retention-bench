"""C11: the in-context (self-authored notes) validation SUT on the CL-Bench path.

Three layers, fastest first:
  * pure unit — the structured-output parsing + minimal-valid fallback that
    guarantee a schema-conforming action so the runner never crashes;
  * in-process — drive ``_handle_query`` with ``_call_llm`` monkeypatched, proving
    the SUT flushes notes before replying AND reads prior notes back on the next
    query (the retention mechanism), without a subprocess or network;
  * subprocess — drive the real ``notes_llm.clbench_main`` process through
    ``SubprocessSystem`` + CL-Bench's runner with the fake-OpenAI shim (no API
    key, no network), proving the wire contract holds end-to-end.

Quality (does the curve actually lift above the prior?) is NOT asserted here —
that needs a live model and an API key; see the C11 debrief for the live run.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("src.interface", reason="cl-benchmark (import 'src') not installed")

# notes_llm is not installed in the venv; put the package dir on sys.path so the
# in-process layers can import it (clbench_main imports no openai at module load).
NOTES_LLM_PKG = Path(__file__).resolve().parent.parent / "suts" / "notes_llm"
if str(NOTES_LLM_PKG) not in sys.path:
    sys.path.insert(0, str(NOTES_LLM_PKG))

from notes_llm import clbench_main  # noqa: E402
from src.tasks.blind_spectrum_monitoring.task import ScanReport  # noqa: E402

SCHEMA = ScanReport.model_json_schema()


# --------------------------------------------------------------------------- #
# Layer 1 — structured-output crash-safety (pure).
# --------------------------------------------------------------------------- #
def test_extract_json_handles_fences_and_prose():
    assert clbench_main._extract_json('{"transmitters": []}') == {"transmitters": []}
    assert clbench_main._extract_json('```json\n{"transmitters": []}\n```') == {"transmitters": []}
    assert clbench_main._extract_json('Sure! {"transmitters": []} done.') == {"transmitters": []}
    assert clbench_main._extract_json("not json at all") is None
    assert clbench_main._extract_json("[1,2,3]") is None  # top-level must be an object


def test_coerce_action_passes_through_valid_model_output():
    parsed = {"transmitters": [
        {"center_freq": 100.0, "bandwidth": 5.0, "currently_active": True, "estimated_power": -30.0}
    ]}
    action = clbench_main._coerce_action(parsed, SCHEMA)
    assert action == parsed
    ScanReport(**action)  # constructs without raising


def test_coerce_action_falls_back_to_minimal_valid_on_garbage():
    # None (unparseable) and a dict missing the required key both → minimal valid.
    for bad in (None, {"unexpected": 1}):
        action = clbench_main._coerce_action(bad, SCHEMA)
        ScanReport(**action)  # the load-bearing guarantee: never crashes the runner
        assert action["transmitters"] == []  # required array → empty list


def test_minimal_valid_builds_required_fields_only():
    val = clbench_main._minimal_valid(SCHEMA, SCHEMA.get("$defs", {}))
    assert val == {"transmitters": []}


# --------------------------------------------------------------------------- #
# Layer 2 — _handle_query in-process: flush-before-reply + read-back on respawn.
# --------------------------------------------------------------------------- #
class _RecordingLLM:
    """Stub for clbench_main._call_llm: returns queued (text, tin, tout) and
    records every (system, user) prompt it was asked, so the test can prove the
    SUT fed prior notes back into the next call."""

    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, client, model, system, user):
        self.calls.append((system, user))
        text, tin, tout = self._scripted.pop(0)
        return text, tin, tout


def _query(prompt: str) -> dict:
    return {"prompt": prompt, "instance_id": "i", "instance_index": 0,
            "response_schema": SCHEMA, "feedback": None}


def test_handle_query_flushes_notes_and_reads_them_back(monkeypatch):
    state_dir = Path(tempfile.mkdtemp(prefix="c11-handle-"))
    notes_path = state_dir / clbench_main.NOTES_FILENAME

    scripted = [
        ("<NOTES>persistent region near 100MHz</NOTES>", 50, 10),   # query 1: notes
        ('{"transmitters": []}', 40, 5),                            # query 1: report
        ("<NOTES>persistent regions near 100MHz and 250MHz</NOTES>", 60, 12),  # query 2: notes
        ('{"transmitters": [{"center_freq": 100.0, "bandwidth": 5.0, '
         '"currently_active": true, "estimated_power": -30.0}]}', 45, 8),       # query 2: report
    ]
    rec = _RecordingLLM(scripted)
    monkeypatch.setattr(clbench_main, "_call_llm", rec)

    # Query 1 — notes flushed to DIR before the reply, action valid.
    reply1 = clbench_main._handle_query(object(), "m", notes_path, _query("scan A: signal at 100MHz"))
    assert notes_path.read_text() == "persistent region near 100MHz"
    ScanReport(**reply1["action"])
    assert reply1["resource"] == {"tokens_in": 90, "tokens_out": 15,
                                  "model_id": "m", "api_call_count": 2}

    # Query 2 — the SUT read the *prior* notes back and fed them to the model
    # (the retention mechanism). The notes-update call (3rd overall) must contain
    # query-1's notes inside its <PRIOR_NOTES> block.
    reply2 = clbench_main._handle_query(object(), "m", notes_path, _query("scan B: signal at 250MHz"))
    notes_update_user_prompt = rec.calls[2][1]
    assert "persistent region near 100MHz" in notes_update_user_prompt
    assert "<PRIOR_NOTES>" in notes_update_user_prompt
    # And the report call (4th) answered from the *updated* notes, not the raw scan.
    report_user_prompt = rec.calls[3][1]
    assert "250MHz" in report_user_prompt
    assert ScanReport(**reply2["action"]).transmitters[0].center_freq == 100.0


def test_handle_query_cold_resume_reads_existing_notes(monkeypatch):
    """A fresh process (new _handle_query, same DIR) conditions on notes left by a
    prior lineage — the post-RESET resume path."""
    state_dir = Path(tempfile.mkdtemp(prefix="c11-resume-"))
    notes_path = state_dir / clbench_main.NOTES_FILENAME
    notes_path.write_text("carried-over structure from before the reset")

    rec = _RecordingLLM([
        ("<NOTES>updated</NOTES>", 10, 2),
        ('{"transmitters": []}', 10, 2),
    ])
    monkeypatch.setattr(clbench_main, "_call_llm", rec)
    clbench_main._handle_query(object(), "m", notes_path, _query("new scan"))

    notes_update_user_prompt = rec.calls[0][1]
    assert "carried-over structure from before the reset" in notes_update_user_prompt


# --------------------------------------------------------------------------- #
# Layer 3 — real subprocess through SubprocessSystem + CL-Bench's runner, with
# the fake-OpenAI shim (no API key, no network).
# --------------------------------------------------------------------------- #
from retention_bench import NoReset, SubprocessSystem  # noqa: E402
from src.interface import TaskResult  # noqa: E402
from src.runtime.runner import run_task  # noqa: E402
from src.tasks.blind_spectrum_monitoring.task import BlindSpectrumMonitoringTask  # noqa: E402

FAKE_SHIM_DIR = Path(__file__).resolve().parent / "fake_openai_shim"
CLBENCH_CMD = ["python", "-m", "notes_llm.clbench_main"]


def _write_responses(path: Path, n_instances: int) -> None:
    """n_instances queries × 2 calls (notes, report), alternating."""
    responses = []
    for i in range(n_instances):
        responses.append({"text": f"<NOTES>seen scan {i}; region near 100MHz persists</NOTES>",
                          "input_tokens": 50, "output_tokens": 10})
        responses.append({"text": '{"transmitters": []}', "input_tokens": 40, "output_tokens": 5})
    import yaml
    path.write_text(yaml.safe_dump({"responses": responses}))


def test_notes_clbench_runs_through_runner(tmp_path, monkeypatch):
    n = 3
    fixture = tmp_path / "responses.yaml"
    _write_responses(fixture, n)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-not-real")
    monkeypatch.setenv("FAKE_OPENAI_FIXTURE", str(fixture))
    monkeypatch.setenv("FAKE_OPENAI_COUNTER", str(tmp_path / "counter"))

    state_dir = tmp_path / "dir"
    system = SubprocessSystem(
        CLBENCH_CMD, state_dir, reset_schedule=NoReset(), name="notes-llm",
        extra_pythonpath=[FAKE_SHIM_DIR, NOTES_LLM_PKG],  # shim shadows openai; pkg resolves -m
    )
    task = BlindSpectrumMonitoringTask(variant="five_ch_wide", num_instances=n, probe_mode=True)
    with system:
        result = run_task(task, system, show_progress=False, reset_between_instances=False)

    assert isinstance(result, TaskResult)
    assert 0.0 <= result.score <= 1.0
    # notes.md was authored in the survive-dir (the retained artifact).
    notes = (state_dir / "notes.md")
    assert notes.is_file() and notes.read_text().strip()
    # All 2n LLM calls landed through the shim (proves the wire contract ran end-
    # to-end and each query made its notes + report call).
    assert (tmp_path / "counter").read_text().strip() == str(2 * n)
