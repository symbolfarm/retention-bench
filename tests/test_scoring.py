"""Scoring primitives: relative ε, post-reset windows, bootstrap CIs.

Pure-function tests over :mod:`retention_bench.scoring` — no harness, no
cl-benchmark, no subprocesses. The integration path (the same primitives wired
through ``run_reset_sweep`` on a live SUT) is covered in
``tests/test_gain_curve.py``.
"""

from __future__ import annotations

import pytest

from retention_bench.scoring import (
    EPSILON,
    band_epsilon,
    bootstrap_mean_ci,
    bootstrap_norm_gain_ci,
    mean_at,
    normalised_retention,
    post_reset_window_indices,
)


# --- band_epsilon ---------------------------------------------------------- #


def test_band_epsilon_scales_with_r_max() -> None:
    assert band_epsilon(1.0) == pytest.approx(EPSILON)
    # The motivating case: 64 scored of 112 instances (the default
    # symbolic_associative_retention schedule) compresses the run-mean range to
    # 64/112, and ε compresses with it.
    assert band_epsilon(64 / 112) == pytest.approx(EPSILON * 64 / 112)


@pytest.mark.parametrize("bad", [0.0, -0.5])
def test_band_epsilon_rejects_nonpositive_r_max(bad: float) -> None:
    with pytest.raises(ValueError):
        band_epsilon(bad)


# --- post_reset_window_indices --------------------------------------------- #


def test_window_after_single_reset() -> None:
    # Reset fired after ordinal 3 → window is ordinals 4,5 (indices 3,4) for m=2.
    assert post_reset_window_indices(10, [3], 2) == [3, 4]


def test_window_truncates_at_run_end() -> None:
    assert post_reset_window_indices(5, [4], 3) == [4]


def test_window_truncates_at_next_reset() -> None:
    # Resets after ordinals 2 and 4 with m=3: the first window may use ordinals
    # 3,4 only (ordinal 4 completes *before* its reset fires, so it belongs to
    # the first window); the second window is ordinals 5,6,7. No overlap.
    assert post_reset_window_indices(10, [2, 4], 3) == [2, 3, 4, 5, 6]


def test_window_every_1_density_yields_every_following_instance() -> None:
    # Resets after every ordinal 1..4 of 5: each window truncates to the single
    # next instance, pooling indices 1..4.
    assert post_reset_window_indices(5, [1, 2, 3, 4], 3) == [1, 2, 3, 4]


def test_window_empty_without_resets() -> None:
    assert post_reset_window_indices(5, [], 3) == []


def test_window_rejects_m_below_one() -> None:
    with pytest.raises(ValueError):
        post_reset_window_indices(5, [1], 0)


def test_mean_at_selection_and_empty() -> None:
    rewards = [1.0, 0.0, 1.0, 1.0]
    assert mean_at(rewards, [0, 2, 3]) == pytest.approx(1.0)
    assert mean_at(rewards, [1, 2]) == pytest.approx(0.5)
    assert mean_at(rewards, []) is None


# --- bootstrap CIs ---------------------------------------------------------- #


def test_bootstrap_mean_ci_is_deterministic_under_seed() -> None:
    rewards = [1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    a = bootstrap_mean_ci(rewards, n_boot=200, seed=7)
    b = bootstrap_mean_ci(rewards, n_boot=200, seed=7)
    assert a == b
    assert a != bootstrap_mean_ci(rewards, n_boot=200, seed=8)


def test_bootstrap_mean_ci_degenerate_rewards_collapse_to_point() -> None:
    assert bootstrap_mean_ci([1.0] * 10, n_boot=100) == (1.0, 1.0)


def test_bootstrap_mean_ci_brackets_the_sample_mean() -> None:
    rewards = [1.0] * 6 + [0.0] * 4  # mean 0.6
    lo, hi = bootstrap_mean_ci(rewards, n_boot=2000, seed=0)
    assert lo <= 0.6 <= hi
    assert lo < hi  # mixed rewards → genuine width


def test_bootstrap_mean_ci_rejects_empty() -> None:
    with pytest.raises(ValueError):
        bootstrap_mean_ci([])


def test_bootstrap_mean_ci_rejects_bad_level() -> None:
    with pytest.raises(ValueError):
        bootstrap_mean_ci([1.0, 0.0], level=1.0)


def test_bootstrap_norm_gain_ci_degenerate_arms_collapse_to_formula() -> None:
    # All-constant arms have no resampling variance, so the CI collapses to
    # exactly normalised_retention(R, P, C).
    point = [0.5] * 8
    prior = [0.0] * 8
    ceiling = [1.0] * 8
    expected = normalised_retention(0.5, 0.0, 1.0, 0.05)
    lo, hi = bootstrap_norm_gain_ci(point, prior, ceiling, 0.05, n_boot=100)
    assert (lo, hi) == (pytest.approx(expected), pytest.approx(expected))


def test_bootstrap_norm_gain_ci_propagates_baseline_uncertainty() -> None:
    # The point arm is constant, but a noisy prior still widens the interval —
    # the CI must not treat P and C as exact. (The point must sit strictly
    # inside the band: at R == C the ratio is 1 for every resampled prior.)
    point = [0.5] * 8
    prior = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
    ceiling = [1.0] * 8
    lo, hi = bootstrap_norm_gain_ci(point, prior, ceiling, 0.05, n_boot=500, seed=1)
    assert lo < hi


def test_bootstrap_norm_gain_ci_rejects_empty_arm() -> None:
    with pytest.raises(ValueError):
        bootstrap_norm_gain_ci([1.0], [], [1.0], 0.05)
