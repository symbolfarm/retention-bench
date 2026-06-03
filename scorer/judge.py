"""LLM-as-judge scorer.

Uses an OpenAI-compatible SDK's tool-use / function calling to get a
schema-validated ``{score, rationale}`` back — not fragile free-text
``json.loads`` of the message body. Single judge at temperature 0.

Model configuration: reads ``RETENTION_BENCH_JUDGE_MODEL`` env var;
falls back to ``DEFAULT_JUDGE_MODEL`` (a frontier *open* model, pinned:
the judge is a measuring instrument, so its model is a recorded
measurement parameter, not a free-varying knob — see B9). The client is
the shared OpenAI-compatible (OpenRouter) idiom used across the SUTs.

Note: the judge is deliberately kept on a stronger model than the SUT
baselines because its verdict quality drives every retention score, and
because function calling is the part open models are flakiest at.

Rationale persistence: the caller (``scorer.aggregate``) is responsible
for collecting the ``(record_id, rationale)`` pairs and writing them to
``scoring.jsonl`` in the run directory. This module's ``score()`` method
returns the rationale as a string; it does not write files.

Judge prompt design:
  - Reason-then-score structure: the model produces a brief rationale
    BEFORE the verdict, which improves reliability for borderline cases.
  - The verdict is extracted via a tool call (``judge_verdict``), so we
    never parse free-text JSON.
  - Gold answer and SUT answer are presented side by side; no question
    text is included because the gold answer is the scoring target.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

DEFAULT_JUDGE_MODEL: str = "moonshotai/kimi-k2.6"
DEFAULT_BASE_URL: str = "https://openrouter.ai/api/v1"

# OpenAI-compatible function schema. The JSON-schema body lives under
# ``function.parameters`` (Anthropic called the same body ``input_schema``).
# Field order matters: ``rationale`` precedes ``score`` so the model reasons
# before it commits to a verdict as it generates the arguments JSON.
_JUDGE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "judge_verdict",
        "description": (
            "Record the scoring verdict after reasoning about whether the SUT's "
            "answer is semantically equivalent to the gold answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rationale": {
                    "type": "string",
                    "description": (
                        "One or two sentences explaining why the SUT answer does "
                        "or does not convey the same meaning as the gold answer."
                    ),
                },
                "score": {
                    "type": "integer",
                    "enum": [0, 1],
                    "description": "1 if semantically equivalent, 0 otherwise.",
                },
            },
            "required": ["rationale", "score"],
        },
    },
}

_SYSTEM_PROMPT = (
    "You are a precise judge for a retention benchmark. "
    "Your job is to decide whether a system-under-test (SUT) answer is "
    "semantically equivalent to the gold answer for a factual recall question. "
    "'Semantically equivalent' means the SUT answer conveys the same core "
    "factual content as the gold answer, allowing for minor paraphrasing, "
    "extra context, or minor wording differences — but NOT for omissions of "
    "key facts, hallucinated additions that change meaning, or outright wrong answers. "
    "Think briefly, then call judge_verdict with your verdict."
)


def _build_user_prompt(question_text: str, gold_answer: str, sut_answer: str) -> str:
    return (
        f"Question: {question_text}\n"
        f"Gold answer: {gold_answer}\n"
        f"SUT answer: {sut_answer}\n\n"
        "Is the SUT answer semantically equivalent to the gold answer? "
        "Reason briefly, then call judge_verdict."
    )


class JudgeScorer:
    """LLM-as-judge scorer using OpenAI function-calling for structured output."""

    def __init__(self) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set; JudgeScorer cannot be initialised."
            )
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "`openai` package is not installed (pip install openai)."
            ) from exc

        self._model = os.environ.get("RETENTION_BENCH_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
        base_url = os.environ.get("RETENTION_BENCH_BASE_URL", DEFAULT_BASE_URL)
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

        # Side-channel accumulators for the judge_resource_appendix (B11).
        # Kept off the Scorer.score() return tuple so ExactMatchScorer stays
        # clean. Read back after a scoring run via resource_appendix().
        self._api_call_count: int = 0
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        # model_id is captured from each response (response.model is the
        # resolved model id); falls back to the requested model.
        self._resolved_model_id: str = self._model

    def score(self, record: Dict[str, Any]) -> Tuple[float, str, Optional[str]]:
        """Score a single record via the LLM judge.

        Always calls the judge for judge-eligible records — no short-circuit
        even for obvious cases, so ``scorer_kind`` is consistent per type.

        Returns
        -------
        score : float
            1.0 if semantically equivalent, 0.0 otherwise.
        scorer_kind : str
            ``"judge"``
        rationale : str
            The judge's textual rationale.
        """
        parsing_status = record.get("parsing_status", "ok")
        if parsing_status != "ok":
            # Non-ok parsing means the harness couldn't extract an answer at
            # all — no point asking the judge. Score 0 with a synthetic
            # rationale so scorer_kind remains "judge" and the record is
            # consistent.
            return (
                0.0,
                "judge",
                f"Skipped judge: parsing_status={parsing_status!r}.",
            )

        question_text = record.get("question_text", "")
        gold_answer = record.get("gold_answer", "") or ""
        sut_answer = record.get("sut_answer", "") or ""

        user_prompt = _build_user_prompt(question_text, gold_answer, sut_answer)

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_JUDGE_TOOL],
            tool_choice={"type": "function", "function": {"name": "judge_verdict"}},
            temperature=0,
        )

        # Accumulate judge spend for the judge_resource_appendix (B11). Only
        # reached when an API call actually happened (the parsing_status != "ok"
        # path returns above without calling the judge).
        self._accumulate_usage(response)

        # Extract the judge_verdict tool-call arguments.
        tool_input = _extract_tool_input(response)
        score = float(tool_input["score"])
        rationale = str(tool_input["rationale"])
        return score, "judge", rationale

    def _accumulate_usage(self, response: Any) -> None:
        """Add one judge response's token usage to the run accumulators."""
        usage = getattr(response, "usage", None)
        if usage is not None:
            self._input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            self._output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        # response.model is the resolved model id from the API; keep it as the
        # appendix's model_id (constant across a run, last write wins).
        resolved = getattr(response, "model", None)
        if resolved:
            self._resolved_model_id = str(resolved)
        self._api_call_count += 1

    def resource_appendix(self) -> Dict[str, Any]:
        """Accumulated judge spend for the run.

        Mirrors the SUT ``resource_appendix`` conventions (``kind: "api"`` +
        ``model_id``; see ``docs/sut-interface.md``) and adds judge-specific
        totals. Written to a sibling ``judge_resource_appendix.jsonl`` by the
        CLI — distinct from the SUT's budget (decision #6 open-Q6).
        """
        return {
            "kind": "api",
            "model_id": self._resolved_model_id,
            "api_call_count": self._api_call_count,
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
        }


def _extract_tool_input(response: Any) -> Dict[str, Any]:
    """Pull the ``judge_verdict`` arguments dict out of an OpenAI-compatible response.

    Unlike Anthropic (where the tool input arrives as an already-parsed dict on a
    ``tool_use`` content block), OpenAI-compatible APIs return the call under
    ``message.tool_calls[*].function.arguments`` as a **JSON string** that must be
    parsed.
    """
    tool_calls = getattr(response.choices[0].message, "tool_calls", None) or []
    for call in tool_calls:
        fn = getattr(call, "function", None)
        if fn is not None and getattr(fn, "name", None) == "judge_verdict":
            return json.loads(fn.arguments)
    raise RuntimeError(
        "judge_verdict tool call not found in response. "
        f"tool_calls: {[getattr(getattr(c, 'function', None), 'name', '?') for c in tool_calls]}"
    )
