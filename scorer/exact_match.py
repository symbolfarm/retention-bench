"""Exact-match scoring for surface-factual questions.

MVP scorer per decision #6A: case-insensitive, whitespace-normalised string
match between ``sut_answer`` and ``gold_answer``. ``parsing_status`` of
``not_found`` or ``ambiguous`` always scores 0 (but remains distinguishable
in the per-record output for diagnostics).
"""

from __future__ import annotations

import re
import string
import unicodedata
from typing import Any, Dict

# Strip standard ASCII punctuation plus the curly quotes that creep in from
# LLM outputs. Conservative — we don't want to over-normalise here; the
# trade-off is documented in the M6 debrief.
_PUNCT_CHARS = string.punctuation + "‘’“”–—"
_PUNCT_RE = re.compile(f"[{re.escape(_PUNCT_CHARS)}]")
_WS_RE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Normalise for case-insensitive, whitespace-collapsed, punctuation-stripped match."""
    # NFKC folds compatibility characters (e.g. full-width to ASCII).
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def exact_match_score(sut_answer: str, gold_answer: str) -> float:
    """Return 1.0 if normalised strings match, else 0.0."""
    return 1.0 if _normalise(sut_answer) == _normalise(gold_answer) else 0.0


def score_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the score for a single ``questions.jsonl`` record.

    Returns a new dict with the original record's fields plus a ``score`` field.
    Records with ``parsing_status`` other than ``ok`` score 0 (per
    ``docs/trace-schema.md`` §"SUT-answer ingestion": the scorer treats
    ``not_found`` and ``ambiguous`` as 0, but they remain distinguishable).
    """
    out = dict(record)
    parsing_status = record.get("parsing_status", "ok")
    if parsing_status != "ok":
        out["score"] = 0.0
        return out
    out["score"] = exact_match_score(
        record.get("sut_answer", "") or "",
        record.get("gold_answer", "") or "",
    )
    return out
