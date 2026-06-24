#!/usr/bin/env bash
# retention-bench convenience wrapper.
#
# Usage:
#   ./run.sh smoke              # canonical offline, keyless smoke (gain curve)
#   ./run.sh ladder             # offline, keyless reference-ladder sweep (floor/partial/full)
#   ./run.sh [gain_curve args]  # arbitrary CL-Bench task; pass-through
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${RETENTION_BENCH_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

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
  exec "$PYTHON_BIN" -m retention_bench.gain_curve \
    --task blind_spectrum_monitoring \
    --task-kwarg variant=five_ch_wide \
    --sut "python -m bsm_accumulator.clbench_main" \
    --extra-pythonpath suts/bsm_accumulator \
    --reset-every 1 --reset-every 2 \
    "$@"
fi

if [[ "$cmd" == "ladder" ]]; then
  shift || true
  # Reference ladder: the three KEYLESS reference SUTs on the same task
  # (symbolic_associative_retention), swept over the reset axis, so their
  # retention curves can be read on one figure (see docs/reference-ladder.md).
  # Offline, no API key, no model weights. Order: floor -> graded -> retainers.
  #   no_state        ephemeral, never touches the survive-dir   -> retention floor
  #   reset_lossy     deterministic reset-coupled loss           -> graded retention (0<norm<1)
  #   bounded_memory  FIFO-capped survive-dir window             -> capacity-limited retainer
  #   associative_memory  full survive-dir persistence           -> full-retention ceiling
  for entry in \
    "no-state-floor:no_state:suts/no_state" \
    "reset-lossy-graded:reset_lossy:suts/reset_lossy" \
    "bounded-memory-partial:bounded_memory:suts/bounded_memory" \
    "associative-memory-full:associative_memory:suts/associative_memory"; do
    name="${entry%%:*}"; rest="${entry#*:}"; pkg="${rest%%:*}"; path="${rest#*:}"
    echo "===== ${name} ====="
    "$PYTHON_BIN" -m retention_bench.gain_curve \
      --task symbolic_associative_retention \
      --sut "python -m ${pkg}.clbench_main" \
      --extra-pythonpath "$path" \
      --reset-every 1 --reset-every 2 \
      --name "$name" "$@"
    echo
  done
  exit 0
fi

# Fall through: pass-through to the gain-curve driver for any other CL-Bench
# task / SUT (it is SUT-agnostic; see `--help` and `--list-tasks`).
exec "$PYTHON_BIN" -m retention_bench.gain_curve "$@"
