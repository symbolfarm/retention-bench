"""Reference-SUT env-var knobs must fail loud, not silently fall back.

`RESET_LOSSY_RATE` and `BOUNDED_MEMORY_CAP` used to catch invalid values (bad
literal or out-of-range) and quietly return the default — for a *benchmark*,
a typo'd experiment parameter silently running the default is worse than a
crash (2026-07-07 review, "Smaller items"). These are fast offline unit tests
against the SUT modules directly (stdlib only, no harness/cl-bench needed).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RESET_LOSSY_PKG = REPO_ROOT / "suts" / "reset_lossy"
BOUNDED_MEMORY_PKG = REPO_ROOT / "suts" / "bounded_memory"
RANDOM_GUESS_PKG = REPO_ROOT / "suts" / "random_guess"
for pkg in (RESET_LOSSY_PKG, BOUNDED_MEMORY_PKG, RANDOM_GUESS_PKG):
    if str(pkg) not in sys.path:
        sys.path.insert(0, str(pkg))

from bounded_memory import clbench_main as bounded_memory_main  # noqa: E402
from random_guess import clbench_main as random_guess_main  # noqa: E402
from reset_lossy import clbench_main as reset_lossy_main  # noqa: E402


# --- RESET_LOSSY_RATE ----------------------------------------------------- #


def test_reset_lossy_rate_default_when_unset(monkeypatch):
    monkeypatch.delenv("RESET_LOSSY_RATE", raising=False)
    assert reset_lossy_main._rate() == reset_lossy_main.DEFAULT_RATE


def test_reset_lossy_rate_accepts_valid_value(monkeypatch):
    monkeypatch.setenv("RESET_LOSSY_RATE", "0.2")
    assert reset_lossy_main._rate() == pytest.approx(0.2)


def test_reset_lossy_rate_raises_on_non_numeric(monkeypatch):
    monkeypatch.setenv("RESET_LOSSY_RATE", "not-a-float")
    with pytest.raises(ValueError, match="RESET_LOSSY_RATE"):
        reset_lossy_main._rate()


@pytest.mark.parametrize("bad_value", ["-0.1", "1.0", "2.5"])
def test_reset_lossy_rate_raises_on_out_of_range(monkeypatch, bad_value):
    monkeypatch.setenv("RESET_LOSSY_RATE", bad_value)
    with pytest.raises(ValueError, match="RESET_LOSSY_RATE"):
        reset_lossy_main._rate()


# --- BOUNDED_MEMORY_CAP ---------------------------------------------------- #


def test_bounded_memory_cap_default_when_unset(monkeypatch):
    monkeypatch.delenv("BOUNDED_MEMORY_CAP", raising=False)
    assert bounded_memory_main._cap() == bounded_memory_main.DEFAULT_CAP


def test_bounded_memory_cap_accepts_valid_value(monkeypatch):
    monkeypatch.setenv("BOUNDED_MEMORY_CAP", "3")
    assert bounded_memory_main._cap() == 3


def test_bounded_memory_cap_raises_on_non_numeric(monkeypatch):
    monkeypatch.setenv("BOUNDED_MEMORY_CAP", "not-an-int")
    with pytest.raises(ValueError, match="BOUNDED_MEMORY_CAP"):
        bounded_memory_main._cap()


def test_bounded_memory_cap_raises_on_out_of_range(monkeypatch):
    monkeypatch.setenv("BOUNDED_MEMORY_CAP", "0")
    with pytest.raises(ValueError, match="BOUNDED_MEMORY_CAP"):
        bounded_memory_main._cap()


# --- RANDOM_GUESS_SEED / RANDOM_GUESS_NUM_ATTRIBUTES ----------------------- #


def test_random_guess_knob_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("RANDOM_GUESS_SEED", raising=False)
    monkeypatch.delenv("RANDOM_GUESS_NUM_ATTRIBUTES", raising=False)
    assert random_guess_main._seed() == random_guess_main.DEFAULT_SEED
    assert random_guess_main._num_attributes() == random_guess_main.DEFAULT_NUM_ATTRIBUTES


def test_random_guess_knobs_accept_valid_values(monkeypatch):
    monkeypatch.setenv("RANDOM_GUESS_SEED", "7")
    monkeypatch.setenv("RANDOM_GUESS_NUM_ATTRIBUTES", "4")
    assert random_guess_main._seed() == 7
    assert random_guess_main._num_attributes() == 4


@pytest.mark.parametrize("bad_value", ["not-an-int", "-1"])
def test_random_guess_seed_raises_on_bad_value(monkeypatch, bad_value):
    monkeypatch.setenv("RANDOM_GUESS_SEED", bad_value)
    with pytest.raises(ValueError, match="RANDOM_GUESS_SEED"):
        random_guess_main._seed()


@pytest.mark.parametrize("bad_value", ["1", "21", "nope"])
def test_random_guess_num_attributes_raises_on_bad_value(monkeypatch, bad_value):
    monkeypatch.setenv("RANDOM_GUESS_NUM_ATTRIBUTES", bad_value)
    with pytest.raises(ValueError, match="RANDOM_GUESS_NUM_ATTRIBUTES"):
        random_guess_main._num_attributes()


def test_random_guess_is_a_pure_function_of_seed_and_prompt():
    """Reproducibility is what makes the chance rung a fixed line rather than a
    fresh sample per arm."""
    vocab = random_guess_main.ATTRIBUTES[:16]
    first = random_guess_main._choose(vocab, 0, "RECALL object_attribute\nobject: norb")
    again = random_guess_main._choose(vocab, 0, "RECALL object_attribute\nobject: norb")
    other_seed = random_guess_main._choose(vocab, 1, "RECALL object_attribute\nobject: norb")
    assert first == again
    assert first in vocab
    assert other_seed in vocab
