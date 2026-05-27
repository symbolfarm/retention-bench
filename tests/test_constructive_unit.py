"""Fast offline unit test for the constructive SUT's core mechanics.

Exercises train -> grow -> checkpoint -> RESET (simulated as a fresh load from
disk) -> reload -> answer on a tiny config. No harness, no network, CPU-only.

The load-bearing claims:
  - training takes real gradient steps (LM loss on seen text drops);
  - growth adds capacity (param_count up, n_layers up, storage-delta > 0);
  - a grown checkpoint round-trips: a fresh State rebuilt from disk has the
    grown shape and identical weights (loss reproduces exactly);
  - post-RESET state reflects pre-RESET reading, not from-scratch (lower LM
    loss on seen text than a cold model + carried-over grown param count);
  - QUIZ generation returns well-formed answers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSTRUCTIVE_PKG = REPO_ROOT / "suts" / "constructive"
if str(CONSTRUCTIVE_PKG) not in sys.path:
    sys.path.insert(0, str(CONSTRUCTIVE_PKG))

from constructive import checkpoint as ckpt  # noqa: E402
from constructive import train as trainer  # noqa: E402
from constructive.model import ModelConfig, grow, text_to_ids  # noqa: E402


TINY = ModelConfig(block_size=16, d_model=16, n_heads=2, n_layers=1)
SEEN_TEXT = "the old man had a pale blue eye, a vulture eye. " * 4


def test_training_reduces_loss_on_seen_text() -> None:
    state = ckpt.cold_init(TINY, seed=0)
    ids = text_to_ids(SEEN_TEXT)
    before = trainer.lm_loss(state, ids)
    steps = trainer.train_on_text(state, ids)
    after = trainer.lm_loss(state, ids)
    assert steps == trainer.STEPS_PER_READ
    assert after < before  # real gradient steps moved the loss down
    assert state.meta.train_steps == steps
    assert state.meta.train_flops > 0


def test_growth_adds_capacity() -> None:
    state = ckpt.cold_init(TINY, seed=0)
    p_before = state.model.param_count()
    layers_before = state.config.n_layers
    state.model = grow(state.config, state.model)
    state.config = state.model.cfg
    assert state.config.n_layers == layers_before + 1
    assert state.model.param_count() > p_before  # storage-delta > 0


def test_grown_checkpoint_roundtrips(tmp_path: Path) -> None:
    state = ckpt.cold_init(TINY, seed=0)
    ids = text_to_ids(SEEN_TEXT)
    trainer.train_on_text(state, ids)
    # Grow, then train once more so the new block carries gradient too.
    state.model = grow(state.config, state.model)
    state.config = state.model.cfg
    state.meta.growth_count += 1
    trainer.train_on_text(state, ids)
    loss_before = trainer.lm_loss(state, ids)

    ckpt.save(tmp_path, state)
    reloaded = ckpt.load(tmp_path)

    # Grown shape rebuilt from saved config before load_state_dict.
    assert reloaded.config.n_layers == TINY.n_layers + 1
    assert reloaded.model.param_count() == state.model.param_count()
    assert reloaded.meta.growth_count == 1
    # Weights identical -> loss reproduces exactly.
    assert abs(trainer.lm_loss(reloaded, ids) - loss_before) < 1e-6


def test_survives_reset_reflects_prior_reading(tmp_path: Path) -> None:
    """Simulate RESET: train+grow+flush, then a fresh load (new process)."""
    ids = text_to_ids(SEEN_TEXT)

    # Session 1: cold init, train, grow, flush checkpoint to DIR.
    s1 = ckpt.cold_init(TINY, seed=0)
    trainer.train_on_text(s1, ids)
    s1.model = grow(s1.config, s1.model)
    s1.config = s1.model.cfg
    s1.meta.growth_count += 1
    trainer.train_on_text(s1, ids)
    ckpt.save(tmp_path, s1)
    trained_loss = trainer.lm_loss(s1, ids)
    grown_params = s1.model.param_count()

    # ---- SIGKILL boundary: nothing in memory survives; only DIR does. ----

    # Session 2: fresh process loads from DIR.
    assert ckpt.has_checkpoint(tmp_path)
    s2 = ckpt.load(tmp_path)

    # A from-scratch model of the *same grown shape* (the wrong baseline a
    # naive reload would give if it ignored the checkpoint weights).
    cold_same_shape = ckpt.cold_init(s2.config, seed=999)
    cold_loss = trainer.lm_loss(cold_same_shape, ids)

    # Post-RESET state reflects pre-RESET reading: carried-over grown param
    # count AND a lower LM loss on seen text than a from-scratch model.
    assert s2.model.param_count() == grown_params
    assert s2.config.n_layers == TINY.n_layers + 1
    assert abs(trainer.lm_loss(s2, ids) - trained_loss) < 1e-6
    assert trainer.lm_loss(s2, ids) < cold_loss


def test_quiz_generation_well_formed() -> None:
    state = ckpt.cold_init(TINY, seed=0)
    from constructive.__main__ import _handle_quiz

    event = {
        "event_id": "evt-0001",
        "event_type": "QUIZ",
        "stage_input": (
            '<QUESTION id="q1">What color is the eye?</QUESTION>\n'
            '<QUESTION id="q2">Who arrives?</QUESTION>'
        ),
    }
    reply = _handle_quiz(state, event)
    assert reply["event_id"] == "evt-0001"
    ids = [a["id"] for a in reply["answers"]]
    assert ids == ["q1", "q2"]
    for a in reply["answers"]:
        assert isinstance(a["text"], str)  # gibberish is acceptable
    assert "param_count=" in reply["notes"]
