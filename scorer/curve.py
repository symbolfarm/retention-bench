"""Render the per-question table and aggregate retention curve to a string.

Plot rendering (matplotlib etc.) is out of scope for MVP per the task brief;
a printed table is sufficient.
"""

from __future__ import annotations

from typing import Dict, List

from scorer.aggregate import (
    EPSILON,
    QuestionAggregate,
    aggregate_curve,
    aggregate_curve_by_type,
    normalised_retention,
)


def render_curve(
    per_question: Dict[str, QuestionAggregate],
    epsilon: float = EPSILON,
) -> str:
    """Render per-question and aggregate retention tables to a string.

    Deterministic: same input → byte-identical output. Question rows are
    ordered by ``question_id``; k columns are ordered ascending.
    """
    lines: List[str] = []
    if not per_question:
        return "(no questions)\n"

    # Discover the set of k values that appear anywhere.
    all_ks = sorted({k for agg in per_question.values() for k in agg.retention.keys()})

    # Header.
    header = ["question_id", "P", "C"]
    for k in all_ks:
        header.append(f"R({k})")
        header.append(f"norm_R({k})")
    lines.append(" | ".join(header))

    # Per-question rows. Sort by question_id for determinism.
    for qid in sorted(per_question.keys()):
        agg = per_question[qid]
        row: List[str] = [qid]
        row.append(_fmt(agg.prior))
        row.append(_fmt(agg.ceiling))
        excluded = agg.is_excluded(epsilon)
        for k in all_ks:
            r = agg.retention_at(k)
            row.append(_fmt(r))
            if r is None:
                row.append("—")
            elif excluded:
                row.append("(excluded — C≈P)")
            else:
                assert agg.prior is not None and agg.ceiling is not None
                row.append(
                    _fmt(normalised_retention(r, agg.prior, agg.ceiling, epsilon))
                )
        lines.append(" | ".join(row))

    # Aggregate rows.
    curve = aggregate_curve(per_question, epsilon)
    lines.append("")
    if not curve:
        lines.append("aggregate: (no usable questions — all excluded or no retention probes)")
    else:
        for k in sorted(curve.keys()):
            mean, n = curve[k]
            lines.append(f"aggregate (k={k}, n_usable={n}): {mean:.2f}")

    # Per-question_type breakdown (B15). Makes the surface_factual-vs-multi_hop
    # separation legible: a flat-high curve across types is a stenography smell;
    # strong surface_factual with collapsing multi_hop is the
    # understanding-transfer signal. See docs/metrics.md for the interpretation
    # rule.
    by_type = aggregate_curve_by_type(per_question, epsilon)
    if by_type:
        lines.append("")
        lines.append("by question_type:")
        for qtype in sorted(by_type.keys()):
            type_curve = by_type[qtype]
            if not type_curve:
                lines.append(f"  {qtype}: (no usable questions — all excluded)")
                continue
            for k in sorted(type_curve.keys()):
                mean, n = type_curve[k]
                lines.append(f"  {qtype} (k={k}, n_usable={n}): {mean:.2f}")

    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"
