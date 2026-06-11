#!/usr/bin/env bash
# retention-bench convenience wrapper.
#
# Usage:
#   ./run.sh smoke              # canonical offline, keyless smoke (gain curve)
#   ./run.sh [gain_curve args]  # arbitrary CL-Bench task; pass-through
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source .env if present so OPENROUTER_API_KEY (and friends) get exported
# without the caller having to remember. Never committed (see .gitignore).
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

cmd="${1:-}"

if [[ "$cmd" == "smoke" ]]; then
  shift || true
  # Canonical smoke: the keyless, offline BSM accumulator SUT driven through the
  # CL-Bench-native gain-curve sweep on blind_spectrum_monitoring. No API key and
  # no model weights — it proves the full reset/retention pipeline end-to-end and
  # prints the P / C / R(k) curve. See suts/bsm_accumulator/README.md.
  exec python3 -m retention_bench.gain_curve \
    --task blind_spectrum_monitoring \
    --task-kwarg variant=five_ch_wide \
    --sut "python -m bsm_accumulator.clbench_main" \
    --extra-pythonpath suts/bsm_accumulator \
    --reset-every 1 --reset-every 2 \
    "$@"
fi

# Fall through: pass-through to the gain-curve driver for any other CL-Bench
# task / SUT (it is SUT-agnostic; see `--help` and `--list-tasks`).
exec python3 -m retention_bench.gain_curve "$@"
