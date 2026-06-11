"""CL-Bench entrypoint for the keyless accumulator SUT.

Driven through ``retention_bench.SubprocessSystem``, which speaks a one-line-JSON
contract over stdin/stdout:

  request  (harness -> SUT):
    {"prompt": str, "instance_id": str|null, "instance_index": int|null,
     "response_schema": {<JSON Schema>}, "feedback": str|null}
  reply    (SUT -> harness):
    {"action": {"transmitters": [<Transmitter>, ...]},
     "resource": {"flops": int, "tokens_in": int, "tokens_out": int,
                  "model_id": str}}

The harness forwards only the rendered ``prompt`` text (not the task's structured
``detected_peaks``), so this module regex-parses peaks out of the
``blind_spectrum_monitoring`` instance template, whose peak lines are stable:

  ``  - peak_id: peak-… | freq: 32.3 MHz | power: -39.0 dBm | width: 14.8 MHz``

Each query: parse this scan's peaks, merge them into the persistent set in the
survive-dir (flushed atomically *before* the reply so it survives a RESET
SIGKILL), then emit a ``ScanReport`` of every transmitter accumulated so far.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

# State file inside the survive-dir (== cwd per the contract). One JSON object:
#   {"<key>": {"center_freq": float, "bandwidth": float, "estimated_power": float}}
# keyed by the quantised (freq, width) so a channel seen on many scans is one
# entry. The interval-IoU scorer merges overlapping reports anyway, so the
# quantisation only keeps the state file tidy.
STATE_FILENAME = "observed_peaks.json"

# `  - peak_id: … | freq: 32.3 MHz | power: -39.0 dBm | width: 14.8 MHz`
_PEAK_RE = re.compile(
    r"freq:\s*(?P<freq>-?\d+(?:\.\d+)?)\s*MHz\s*\|\s*"
    r"power:\s*(?P<power>-?\d+(?:\.\d+)?)\s*dBm\s*\|\s*"
    r"width:\s*(?P<width>-?\d+(?:\.\d+)?)\s*MHz"
)


def _dir_path() -> Path:
    # cwd is the survive-dir per the contract; RETENTION_BENCH_DIR echoes it.
    return Path(os.environ.get("RETENTION_BENCH_DIR", os.getcwd()))


def _peak_key(freq: float, width: float) -> str:
    """Quantise (freq, width) so the same channel collapses to one entry."""
    return f"{round(freq, 1)}:{round(width, 1)}"


def _parse_peaks(prompt: str) -> dict[str, dict[str, float]]:
    """Extract this scan's peaks from the rendered prompt, keyed by _peak_key."""
    found: dict[str, dict[str, float]] = {}
    for m in _PEAK_RE.finditer(prompt):
        freq = float(m.group("freq"))
        width = float(m.group("width"))
        power = float(m.group("power"))
        found[_peak_key(freq, width)] = {
            "center_freq": freq,
            "bandwidth": width,
            "estimated_power": power,
        }
    return found


def _load_state(dir_path: Path) -> dict[str, dict[str, float]]:
    path = dir_path / STATE_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(dir_path: Path, state: dict[str, dict[str, float]]) -> None:
    """Atomic write so a RESET SIGKILL can't leave a half-written state file."""
    path = dir_path / STATE_FILENAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, path)  # atomic on POSIX


def _handle_query(state: dict[str, dict[str, float]], dir_path: Path, request: dict) -> dict:
    prompt = request.get("prompt") or ""
    this_scan = _parse_peaks(prompt)

    # Merge this scan's peaks into the persistent set, refreshing power readings.
    for key, peak in this_scan.items():
        state[key] = peak

    # Flush *before* replying: the bytes must survive a hard-reset SIGKILL.
    _save_state(dir_path, state)

    transmitters = [
        {
            "center_freq": peak["center_freq"],
            "bandwidth": peak["bandwidth"],
            # Active iff this region was detected on the *current* scan; otherwise
            # it's a remembered (currently-dormant) transmitter.
            "currently_active": key in this_scan,
            "estimated_power": peak["estimated_power"],
        }
        for key, peak in state.items()
    ]

    resource = {
        # Toy monotone compute signal so the SubprocessSystem compute channel has
        # something to carry (no real FLOPs — this SUT does no arithmetic model).
        "flops": 100 * len(transmitters),
        "tokens_in": len(prompt) // 4,
        "tokens_out": len(transmitters),
        "model_id": "bsm-accumulator",
    }
    return {"action": {"transmitters": transmitters}, "resource": resource}


def _iter_requests(stream: Iterable[str]) -> Iterator[dict]:
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


def main() -> None:
    dir_path = _dir_path()
    state = _load_state(dir_path)
    for request in _iter_requests(sys.stdin):
        reply = _handle_query(state, dir_path, request)
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
