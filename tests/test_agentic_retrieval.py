from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "suts" / "agentic_retrieval"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from agentic_retrieval import clbench_main as m


class Usage:
    prompt_tokens = 12
    completion_tokens = 3
    model_extra = {"cost": 0.00001}


class Message:
    content = '{"answer":"bin-a"}'


class Choice:
    message = Message()


class Response:
    choices = [Choice()]
    usage = Usage()


class Completions:
    def create(self, **kwargs):
        return Response()


class Chat:
    completions = Completions()


class Client:
    chat = Chat()


def req(prompt):
    return {"prompt": prompt, "instance_id": "x", "response_schema": {
        "type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}}


def run(request, tmp_path):
    return m.handle(request, Client(), m.DEFAULT_MODEL,
                    tmp_path / "facts.jsonl", tmp_path / ".harness" / "trace.jsonl")


def test_transfer_performs_two_dependent_disk_lookups(tmp_path):
    run(req("TRAIN object_attribute\nobject: norb\nattribute: red\nrole: bridge\nReply exactly: stored"), tmp_path)
    run(req("TRAIN attribute_bin_rule\nattribute: red\nbin: bin-a\nReply exactly: stored"), tmp_path)
    reply = run(req("TRANSFER object_bin\nobject: norb\nwhich bin?"), tmp_path)
    assert reply["action"] == {"answer": "bin-a"}
    row = json.loads((tmp_path / ".harness" / "trace.jsonl").read_text().splitlines()[-1])
    assert row["retrieval_count"] == 2
    assert [x["query"] for x in row["lookups"]] == ["object:norb", "attribute:red"]


def test_recall_performs_one_lookup_and_training_uses_no_api(tmp_path):
    train = run(req("TRAIN object_attribute\nobject: norb\nattribute: red\nrole: bridge\nReply exactly: stored"), tmp_path)
    recall = run(req("RECALL object_attribute\nobject: norb\nwhat attribute?"), tmp_path)
    assert train["resource"]["api_call_count"] == 0
    assert recall["resource"]["api_call_count"] == 1
    assert json.loads((tmp_path / ".harness" / "trace.jsonl").read_text().splitlines()[-1])["retrieval_count"] == 1


def test_missing_store_still_returns_schema_valid_answer(tmp_path):
    reply = run(req("TRANSFER object_bin\nobject: missing\nwhich bin?"), tmp_path)
    assert isinstance(reply["action"]["answer"], str)
