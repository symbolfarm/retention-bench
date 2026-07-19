"""Retention-curve band normalisation + uncertainty primitives.

The single shared home for the ``(R − P) / max(C − P, ε)`` band formula, its
exclusion threshold ``ε``, and (since RB-12) the metric machinery that makes a
curve point trustworthy: percentile-bootstrap confidence intervals over the
per-instance outcomes, and the post-reset-window selection that separates
"retained" from "relearned fast". :mod:`retention_bench.gain_curve` imports
from here so the reset-axis curve and any future consumer normalise against
one definition rather than re-deriving a competing one.

Follows ``docs/metrics.md``:

- ``normalised_retention(R, P, C) = (R − P) / max(C − P, ε)``.
- ``ε`` is *relative to the task's achievable range*: the absolute exclusion
  threshold is ``EPSILON × r_max`` (see :func:`band_epsilon`). A run-mean on a
  task whose schedule leaves some instances structurally unscored (e.g.
  ``r_max = 16/26``) is compressed by exactly ``r_max``, so an absolute 0.05
  would silently demand ~8% of the *achievable* range there while asking 5%
  elsewhere.
- A band where ``C − P < ε`` has no learnable signal; the caller is responsible
  for excluding it (``gain_curve`` reports ``None`` for such points).

History: this module used to live at ``scorer/aggregate.py``, home to the
book-track per-question scorer (retired by C20). Only the band math survived
that cutover; RB-11 folded it into the ``retention_bench`` package proper so
the ``retention-bench`` console script resolves under a non-editable install
(``scorer`` was never a packaged distribution). ``scorer.aggregate`` now
re-exports from here as a thin backward-compatible shim.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

# Band-exclusion threshold as a fraction of the achievable score range
# (``r_max``). Binary rewards on a fully-scored schedule have ``r_max = 1``,
# where this reads as the historical "at least 5% of the score range".
EPSILON: float = 0.05


def band_epsilon(r_max: float, relative: float = EPSILON) -> float:
    """Absolute exclusion threshold for a task whose run-mean tops out at ``r_max``.

    ``r_max`` is CL-Bench's per-task ClassVar: the mean per-instance maximum
    reward for the schedule actually run (a schedule with unscored train
    instances has ``r_max < 1`` even for binary rewards).
    """
    if r_max <= 0:
        raise ValueError(f"band_epsilon needs r_max > 0, got {r_max}")
    return relative * r_max


def normalised_retention(
    r: float, p: float, c: float, epsilon: float = EPSILON
) -> float:
    """``(R − P) / max(C − P, ε)``. Caller is responsible for ε-exclusion."""
    return (r - p) / max(c - p, epsilon)


# --------------------------------------------------------------------------- #
# Post-reset windows (RB-12).
#
# Whole-run R(k) averages the reset's damage against every instance the reset
# could not have affected, so a SUT that *relearns quickly* after a reset is
# indistinguishable from one that *retained*. The window metric looks only at
# the first ``m`` instances after each hard reset — the instances where
# retained state and relearning have not yet converged.
# --------------------------------------------------------------------------- #
def post_reset_window_indices(
    n_instances: int, reset_ordinals: Sequence[int], m: int
) -> list[int]:
    """0-based run-order indices of the first ``m`` instances after each reset.

    ``reset_ordinals`` are the 1-based ordinals of the completed instances
    *after which* a hard reset fired (``SubprocessSystem.reset_ordinals``), so
    the window for a reset at ordinal ``b`` starts at ordinal ``b + 1``. Each
    window is truncated at the run end and at the next reset: an instance
    completed at the next reset's ordinal is still pre-that-reset (the bounce
    fires after it completes) and so belongs to the *current* window, while
    everything later belongs to the next reset's window. Windows therefore
    never overlap; the pooled indices are returned sorted.
    """
    if m < 1:
        raise ValueError(f"post-reset window size m must be >= 1, got {m}")
    ordinals = sorted(set(int(b) for b in reset_ordinals))
    indices: list[int] = []
    for i, b in enumerate(ordinals):
        nxt = ordinals[i + 1] if i + 1 < len(ordinals) else n_instances
        hi = min(b + m, nxt, n_instances)
        indices.extend(range(b, hi))  # ordinals b+1..hi are indices b..hi-1
    return indices


def mean_at(rewards: Sequence[float], indices: Sequence[int]) -> Optional[float]:
    """Mean of ``rewards`` at ``indices``; ``None`` for an empty selection."""
    if not indices:
        return None
    return sum(rewards[i] for i in indices) / len(indices)


# --------------------------------------------------------------------------- #
# Percentile bootstrap (RB-12).
#
# Every arm is a single run of ~26–90 binary-reward instances, so a point's
# reward resolution is comparable to the band threshold itself; the CI makes
# that visible instead of leaving a one-run point to be read as exact. Plain
# percentile bootstrap over the per-instance outcomes, stdlib-only and
# deterministic under a fixed seed.
# --------------------------------------------------------------------------- #
def _percentile_interval(stats: list[float], level: float) -> tuple[float, float]:
    if not 0.0 < level < 1.0:
        raise ValueError(f"CI level must be in (0, 1), got {level}")
    ordered = sorted(stats)
    last = len(ordered) - 1
    alpha = (1.0 - level) / 2.0
    lo = ordered[round(alpha * last)]
    hi = ordered[round((1.0 - alpha) * last)]
    return (lo, hi)


def bootstrap_mean_ci(
    rewards: Sequence[float],
    *,
    n_boot: int = 1000,
    level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile-bootstrap CI for the mean per-instance reward of one arm."""
    if not rewards:
        raise ValueError("bootstrap_mean_ci needs at least one reward")
    rng = random.Random(seed)
    n = len(rewards)
    means = [sum(rng.choices(rewards, k=n)) / n for _ in range(n_boot)]
    return _percentile_interval(means, level)


def bootstrap_norm_gain_ci(
    point_rewards: Sequence[float],
    prior_rewards: Sequence[float],
    ceiling_rewards: Sequence[float],
    epsilon: float,
    *,
    n_boot: int = 1000,
    level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile-bootstrap CI for ``normalised_retention(R(k), P, C)``.

    All three arms are independent runs, so each replicate resamples each
    arm's per-instance rewards independently and recomputes the normalised
    gain. Prior/ceiling uncertainty therefore propagates into the interval —
    a band sitting near ``ε`` yields an honestly wide CI, not a false-precise
    point.
    """
    if not (point_rewards and prior_rewards and ceiling_rewards):
        raise ValueError("bootstrap_norm_gain_ci needs non-empty rewards for all three arms")
    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(n_boot):
        r = sum(rng.choices(point_rewards, k=len(point_rewards))) / len(point_rewards)
        p = sum(rng.choices(prior_rewards, k=len(prior_rewards))) / len(prior_rewards)
        c = sum(rng.choices(ceiling_rewards, k=len(ceiling_rewards))) / len(ceiling_rewards)
        stats.append(normalised_retention(r, p, c, epsilon))
    return _percentile_interval(stats, level)
