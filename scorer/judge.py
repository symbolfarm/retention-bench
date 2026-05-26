"""LLM-as-judge scorer.

Uses the Anthropic SDK's tool-use / structured output to get a
schema-validated ``{score, rationale}`` back — not fragile free-text
``json.loads``. Single judge at temperature 0.

Model configuration: reads ``RETENTION_BENCH_JUDGE_MODEL`` env var;
falls back to ``DEFAULT_JUDGE_MODEL``. This matches the idiom used in
the SUT implementations (see ``suts/no_state/no_state/__main__.py``) so
that task B9 (unify LLM call sites) can replace all of them uniformly.

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

import os
from typing import Any, Dict, Optional, Tuple

DEFAULT_JUDGE_MODEL: str = "claude-sonnet-4-6"

_JUDGE_TOOL: Dict[str, Any] = {
    "name": "judge_verdict",
    "description": (
        "Record the scoring verdict after reasoning about whether the SUT's "
        "answer is semantically equivalent to the gold answer."
    ),
    "input_schema": {
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
    """LLM-as-judge scorer using Anthropic tool-use for structured output."""

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; JudgeScorer cannot be initialised."
            )
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "`anthropic` package is not installed (pip install anthropic)."
            ) from exc

        self._model = os.environ.get("RETENTION_BENCH_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
        self._client = anthropic.Anthropic(api_key=api_key)

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

        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[_JUDGE_TOOL],
            tool_choice={"type": "any"},
            temperature=0,
        )

        # Extract the tool_use block.
        tool_input = _extract_tool_input(response)
        score = float(tool_input["score"])
        rationale = str(tool_input["rationale"])
        return score, "judge", rationale


def _extract_tool_input(response: Any) -> Dict[str, Any]:
    """Pull the ``judge_verdict`` tool input dict out of the Anthropic response."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "judge_verdict":
            return block.input  # type: ignore[return-value]
    raise RuntimeError(
        f"judge_verdict tool call not found in response. "
        f"Content blocks: {[getattr(b, 'type', '?') for b in response.content]}"
    )
