"""CL-Bench entrypoint for the random-guess reference SUT — the measured chance line.

This SUT does not learn and does not retain. It answers every RECALL probe with
a uniformly random *attribute* and every TRANSFER probe with a uniformly random
*bin*, drawn from ``symbolic_associative_retention``'s vocabulary. It never
reads or writes the survive-dir and keeps no in-RAM memory either, so its score
is the same at every point of the reset axis: it *is* the chance line.

### Why the ladder needs a measured chance rung

``no_state`` floors at 0.000 because it answers ``unknown`` rather than
guessing. That is an honest floor for a program, but it invites the obvious
objection — "your floor SUT declines to answer; a real system would guess". A
model *will* guess. Before RB-16 the task had two attributes and two bins, so a
constant guesser scored 0.5 on both probe families (≈0.308 run-mean) — exactly
the published ``reset_lossy`` number, i.e. a coin flip was indistinguishable
from the rung described as partial retention. RB-16 widened the task to 16
attributes/bins (chance 1/16) *and* added this rung so the chance line is
**measured and visible on the same axis** as everything else, not inferred.

### Deterministic, but a single draw

The answer for a prompt is a pure function of ``(seed, prompt)`` — BLAKE2b over
both, taken modulo the vocabulary size — so the SUT is reproducible, is
identical across every arm of the sweep (which is what makes its ``R(k)`` a flat
line), and needs no RNG state to carry across a hard reset. Being one fixed draw
rather than an expectation, its measured score is a sample near, not exactly at,
the analytic chance level ``1/num_attributes``; ``docs/reference-ladder.md``
states both.

### Band behaviour: excluded, by construction

``P`` (stateless prior), ``C`` (no-reset ceiling) and every ``R(k)`` are the
same number for this SUT, so the learnable band ``C - P`` is zero and the
gain-curve driver marks the band **EXCLUDED** — normalised retention is
undefined for a system with nothing to retain. That is the correct reading: the
rung's job is to place the *raw* ``R(k)`` chance line, so that a leaky rung can
be read as above or below chance.

### Knobs

* ``RANDOM_GUESS_SEED`` — int, default ``DEFAULT_SEED``. Chooses which draw.
* ``RANDOM_GUESS_NUM_ATTRIBUTES`` — int in ``[2, len(ATTRIBUTES)]``, default
  ``DEFAULT_NUM_ATTRIBUTES``; must match the task's ``num_attributes`` for the
  guess to be uniform over exactly the vocabulary in play.

Both fail loud on a bad value rather than silently falling back to the default:
for a benchmark, a typo'd experiment parameter running the default unnoticed is
worse than a crash.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Iterable, Iterator

# Vocabulary duplicated (not imported) from
# ``retention_bench/tasks/symbolic_associative_retention.py`` so this SUT stays
# a dependency-free package like the other reference SUTs. Drift would silently
# change the chance level, so ``tests/test_random_guess_clbench.py`` asserts the
# two tuples agree.
ATTRIBUTES = (
    "red", "blue", "vint", "korel", "sabo", "quen",
    "thal", "mirek", "oshan", "drivo", "plent", "yura",
    "gemsa", "nuvo", "hastel", "erkin", "cadro", "umbek",
    "zephy", "lodra",
)
BINS = tuple(f"bin-{c}" for c in "abcdefghijklmnopqrst")

DEFAULT_SEED = 0
DEFAULT_NUM_ATTRIBUTES = 16


def _int_env(name: str, default: int, minimum: int, maximum: int | None = None) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an int, got {raw!r}") from exc
    if value < minimum or (maximum is not None and value > maximum):
        bound = f">= {minimum}" if maximum is None else f"in [{minimum}, {maximum}]"
        raise ValueError(f"{name} must be {bound}, got {value!r}")
    return value


def _seed() -> int:
    return _int_env("RANDOM_GUESS_SEED", DEFAULT_SEED, minimum=0)


def _num_attributes() -> int:
    return _int_env(
        "RANDOM_GUESS_NUM_ATTRIBUTES",
        DEFAULT_NUM_ATTRIBUTES,
        minimum=2,
        maximum=len(ATTRIBUTES),
    )


def _choose(vocabulary: tuple[str, ...], seed: int, prompt: str) -> str:
    """Pick one entry as a pure function of (seed, prompt) — no RNG state."""
    digest = hashlib.blake2b(f"{seed}\x1f{prompt}".encode(), digest_size=8).digest()
    return vocabulary[int.from_bytes(digest, "big") % len(vocabulary)]


def _handle_query(seed: int, num_attributes: int, request: dict[str, Any]) -> dict[str, Any]:
    prompt = str(request.get("prompt") or "")
    attributes = ATTRIBUTES[:num_attributes]
    bins = BINS[:num_attributes]
    answer = "unknown"

    if prompt.startswith("TRAIN "):
        # Nothing is learned; the acknowledgement is still the protocol's
        # expected reply, and train instances are unscored either way.
        answer = "stored"
    elif prompt.startswith("RECALL object_attribute"):
        answer = _choose(attributes, seed, prompt)
    elif prompt.startswith("TRANSFER object_bin"):
        answer = _choose(bins, seed, prompt)

    resource = {
        # One hash per query; no state is ever built.
        "flops": 25,
        "tokens_in": len(prompt) // 4,
        "tokens_out": 1,
        "model_id": "random-guess",
    }
    return {"action": {"answer": answer}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    seed = _seed()
    num_attributes = _num_attributes()
    for request in _iter_requests(sys.stdin):
        reply = _handle_query(seed, num_attributes, request)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
