"""CL-Bench entrypoint for the consolidating-memory reference SUT.

The phased store-removal ladder's variable rung. It answers the same
``symbolic_associative_retention`` TRAIN/RECALL/TRANSFER protocol as
``associative_memory``, but splits its state the way
``docs/phased-store-removal.md`` requires of any SUT the protocol is valid for:

* the **episodic buffer** is an in-RAM list of every fact seen this process,
  never written to the survive-dir, so a hard RESET (SIGKILL) destroys it;
* the **consolidated artifact** is a derived map written to the survive-dir, and
  it holds a deterministic fraction of the episodes rather than all of them.

``CONSOLIDATION_FRACTION`` sets that fraction (and ``CONSOLIDATION_SELECTOR``
chooses *which* episodes migrate at that rate), and it is the only thing that
differs between the ladder's rungs — so the ladder varies *migration behaviour*
with retention mechanism, prompt parsing and scoring held constant. At 1.0 every
episode migrates and the probe phase should reach the ceiling ``C``; at 0.0
nothing migrates and it should fall to the prior ``P``; in between it should land
strictly between, which is what shows the protocol has resolution rather than
being a pass/fail.

Selection is by episode ordinal, not by sampling: episode ``i`` (0-based, in
arrival order) migrates iff ``(i * numerator) % denominator < numerator``, the
standard evenly-spread integer test. Deterministic, and it spreads the migrated
episodes across the whole training sequence instead of taking a prefix — a
prefix would confound "half migrated" with "trained on half as long", and the
uniform ladder already has a rung (``bounded_memory``) whose losses are
positional.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Iterator

STATE_FILENAME = "consolidated.json"
DEFAULT_FRACTION = "1.0"
DEFAULT_SELECTOR = "ordinal"
DEFAULT_BATCH = 8
SELECTORS = ("ordinal", "hashed")

_OBJECT_RE = re.compile(r"^object:\s*(?P<object>\S+)\s*$", re.MULTILINE)
_ATTRIBUTE_RE = re.compile(r"^attribute:\s*(?P<attribute>\S+)\s*$", re.MULTILINE)
_BIN_RE = re.compile(r"^bin:\s*(?P<bin>\S+)\s*$", re.MULTILINE)


def _dir_path() -> Path:
    return Path(os.environ.get("RETENTION_BENCH_DIR", os.getcwd()))


def _fraction() -> Fraction:
    raw = os.environ.get("CONSOLIDATION_FRACTION", DEFAULT_FRACTION)
    try:
        value = Fraction(raw)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(
            f"CONSOLIDATION_FRACTION must be a number, got {raw!r}"
        ) from exc
    if not 0 <= value <= 1:
        raise ValueError(
            f"CONSOLIDATION_FRACTION must be within [0, 1], got {raw!r}"
        )
    return value


def _batch() -> int:
    raw = os.environ.get("CONSOLIDATION_BATCH")
    if raw is None:
        return DEFAULT_BATCH
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"CONSOLIDATION_BATCH must be an int, got {raw!r}") from exc
    if value < 1:
        raise ValueError(f"CONSOLIDATION_BATCH must be >= 1, got {raw!r}")
    return value


def _selector() -> str:
    raw = os.environ.get("CONSOLIDATION_SELECTOR", DEFAULT_SELECTOR)
    if raw not in SELECTORS:
        raise ValueError(
            f"CONSOLIDATION_SELECTOR must be one of {SELECTORS}, got {raw!r}"
        )
    return raw


def _empty_map() -> dict[str, dict[str, str]]:
    return {"object_attributes": {}, "attribute_bins": {}}


def _load_consolidated(dir_path: Path) -> dict[str, dict[str, str]]:
    path = dir_path / STATE_FILENAME
    if not path.exists():
        return _empty_map()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _empty_map()
    if not isinstance(data, dict):
        return _empty_map()
    loaded = _empty_map()
    for key in loaded:
        value = data.get(key)
        if isinstance(value, dict):
            loaded[key] = {str(k): str(v) for k, v in value.items()}
    return loaded


def _save_consolidated(dir_path: Path, consolidated: dict[str, dict[str, str]]) -> None:
    path = dir_path / STATE_FILENAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(consolidated, sort_keys=True))
    os.replace(tmp, path)


def _migrates_by_ordinal(ordinal: int, fraction: Fraction) -> bool:
    """Evenly spread selection of ``fraction`` of episodes by arrival ordinal."""
    numerator, denominator = fraction.numerator, fraction.denominator
    if numerator == 0:
        return False
    return (ordinal * numerator) % denominator < numerator


def _migrates_by_hash(kind: str, key: str, fraction: Fraction) -> bool:
    """Select on a stable hash of the fact itself, ignoring arrival order.

    The ordinal selector interacts with a task whose facts are laid out
    modularly: ``symbolic_associative_retention`` gives object ``i`` attribute
    ``i % A``, so an every-other-episode selection migrates exactly the objects
    whose rules it also migrates, and 2-hop transfer survives at the same rate
    as 1-hop recall. That is a real property of that pairing, not a defect, but
    a ladder whose middle rung depends on it is measuring the alignment as much
    as the protocol. This selector breaks the alignment: whether a fact migrates
    is independent of every other fact, so transfer survives at roughly the
    square of the recall rate. Running both is how the ladder shows which part
    of the number comes from the protocol and which from the task's structure.
    """
    if fraction == 0:
        return False
    digest = hashlib.sha256(f"{kind}\x00{key}".encode()).digest()
    draw = Fraction(int.from_bytes(digest[:8], "big"), 1 << 64)
    return draw < fraction


def _match(pattern: re.Pattern[str], prompt: str) -> str | None:
    found = pattern.search(prompt)
    return found.group(1).strip().lower() if found else None


class Sut:
    def __init__(
        self, dir_path: Path, fraction: Fraction, selector: str, batch: int
    ) -> None:
        self.dir_path = dir_path
        self.fraction = fraction
        self.selector = selector
        self.batch = batch
        # Episodes seen since the last consolidation pass. Nothing here has
        # migrated yet, so a RESET now loses all of it.
        self.pending: list[tuple[int, str, str, str]] = []
        # Volatile: everything this process has been taught. Never persisted.
        self.buffer = _empty_map()
        # Durable: what has migrated, including anything a previous process
        # consolidated before the reset.
        self.consolidated = _load_consolidated(dir_path)
        self.episodes = 0

    def _learn(self, kind: str, key: str, value: str) -> None:
        self.buffer[kind][key] = value
        self.pending.append((self.episodes, kind, key, value))
        self.episodes += 1
        if len(self.pending) >= self.batch:
            self._consolidate()

    def _consolidate(self) -> None:
        """Replay the pending buffer and write the selected part to the artifact.

        Consolidation is a *batch* pass over buffered episodes, not a write on
        every fact, because that is what makes the phased protocol worth running:
        a system that only integrates in batches loses everything still pending
        when its process is killed. Under ``--reset-every 1`` the buffer never
        reaches the batch size, so nothing ever migrates and the run scores the
        floor — the same signature the real learned SUT shows in
        ``docs/phased-store-removal.md``, where the uniform arm reads 0.000 and
        the phased arm 1.000 on identical machinery.
        """
        migrated = False
        for ordinal, kind, key, value in self.pending:
            if self._migrates(ordinal, kind, key):
                self.consolidated[kind][key] = value
                migrated = True
        self.pending.clear()
        if migrated:
            _save_consolidated(self.dir_path, self.consolidated)

    def _migrates(self, ordinal: int, kind: str, key: str) -> bool:
        if self.selector == "hashed":
            return _migrates_by_hash(kind, key, self.fraction)
        return _migrates_by_ordinal(ordinal, self.fraction)

    def _recall(self, kind: str, key: str | None) -> str | None:
        if key is None:
            return None
        # The buffer is the live episodic store; the artifact is what survived.
        # After a RESET the buffer is empty and only the artifact can answer.
        return self.buffer[kind].get(key) or self.consolidated[kind].get(key)

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        prompt = str(request.get("prompt") or "")
        answer = "unknown"

        if prompt.startswith("TRAIN object_attribute"):
            obj = _match(_OBJECT_RE, prompt)
            attr = _match(_ATTRIBUTE_RE, prompt)
            if obj and attr:
                self._learn("object_attributes", obj, attr)
            answer = "stored"
        elif prompt.startswith("TRAIN attribute_bin_rule"):
            attr = _match(_ATTRIBUTE_RE, prompt)
            bin_name = _match(_BIN_RE, prompt)
            if attr and bin_name:
                self._learn("attribute_bins", attr, bin_name)
            answer = "stored"
        elif prompt.startswith("RECALL object_attribute"):
            answer = self._recall("object_attributes", _match(_OBJECT_RE, prompt)) or "unknown"
        elif prompt.startswith("TRANSFER object_bin"):
            attr = self._recall("object_attributes", _match(_OBJECT_RE, prompt))
            answer = self._recall("attribute_bins", attr) or "unknown"

        resource = {
            "flops": 25 * (
                len(self.consolidated["object_attributes"])
                + len(self.consolidated["attribute_bins"])
            ),
            "tokens_in": len(prompt) // 4,
            "tokens_out": 1,
            "model_id": "consolidating-memory",
        }
        return {"action": {"answer": answer}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    sut = Sut(_dir_path(), _fraction(), _selector(), _batch())
    for request in _iter_requests(sys.stdin):
        reply = sut.handle(request)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
