#!/usr/bin/env bash
# retention-bench convenience wrapper.
#
# Usage:
#   ./run.sh smoke              # canonical offline, keyless smoke (gain curve)
#   ./run.sh ladder             # offline, keyless reference-ladder sweep (floor/partial/full)
#   ./run.sh ladder-phased      # offline, keyless PHASED store-removal ladder (--reset-at)
#   ./run.sh decisions [check]  # regenerate the decision-record renderings
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
  # Reference ladder: the KEYLESS reference SUTs on the same task
  # (symbolic_associative_retention), swept over the reset axis, so their
  # retention curves can be read on one figure (see docs/reference-ladder.md).
  # Offline, no API key, no model weights. Order: chance -> floor -> graded -> retainers.
  #   random_guess    stateless uniform guesser                  -> measured chance line (band EXCLUDED)
  #   no_state        ephemeral, never touches the survive-dir   -> retention floor
  #   reset_lossy     deterministic reset-coupled loss           -> graded retention (0<norm<1)
  #   bounded_memory  FIFO-capped survive-dir window             -> capacity-limited retainer
  #   associative_memory  full survive-dir persistence           -> full-retention ceiling
  for entry in \
    "random-guess-chance:random_guess:suts/random_guess" \
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

if [[ "$cmd" == "ladder-phased" ]]; then
  shift || true
  # Phased store-removal ladder: the calibration ladder for `--reset-at`, the
  # protocol that asks whether capability MIGRATED into the durable artifact
  # (see docs/phased-store-removal.md). Offline, no API key, no model weights.
  #
  # Every rung runs BOTH arms in one table — phased (boundaries:48, the single
  # reset at the train/probe boundary) and uniform (every_1) — because the
  # phased number alone does not identify consolidation. A SUT that persists its
  # raw store to the survive-dir scores 1.000 phased for the wrong reason; only
  # the uniform arm separates it from one that consolidates in batches.
  #
  #   random-guess-chance         chance line under the phased protocol (band EXCLUDED)
  #   no-state-floor              in-RAM only, nothing persisted        -> floor
  #   consolidate-none            batch consolidator, fraction 0.0      -> floor, mechanism held constant
  #   consolidate-partial         batch consolidator, fraction 0.5      -> strictly between
  #   consolidate-partial-hashed  fraction 0.5, alignment-free selector -> strictly between
  #   consolidate-full            batch consolidator, fraction 1.0      -> ceiling; uniform arm 0.000
  #   raw-store-control           associative_memory, raw store on disk -> ceiling in BOTH arms (contract violation)
  #
  # The train/probe boundary of symbolic_associative_retention's default
  # 112-instance schedule is ordinal 48.
  for entry in \
    "random-guess-chance:random_guess:suts/random_guess::" \
    "no-state-floor:no_state:suts/no_state::" \
    "consolidate-none:consolidating_memory:suts/consolidating_memory:CONSOLIDATION_FRACTION=0.0:" \
    "consolidate-partial:consolidating_memory:suts/consolidating_memory:CONSOLIDATION_FRACTION=0.5:" \
    "consolidate-partial-hashed:consolidating_memory:suts/consolidating_memory:CONSOLIDATION_FRACTION=0.5:CONSOLIDATION_SELECTOR=hashed" \
    "consolidate-full:consolidating_memory:suts/consolidating_memory:CONSOLIDATION_FRACTION=1.0:" \
    "raw-store-control:associative_memory:suts/associative_memory::"; do
    IFS=':' read -r name pkg path env1 env2 <<<"$entry"
    echo "===== ${name} ====="
    env ${env1:+"$env1"} ${env2:+"$env2"} "$PYTHON_BIN" -m retention_bench.gain_curve \
      --task symbolic_associative_retention \
      --sut "python -m ${pkg}.clbench_main" \
      --extra-pythonpath "$path" \
      --reset-at "48" --reset-every 1 \
      --name "$name" "$@"
    echo
  done
  exit 0
fi

if [[ "$cmd" == "decisions" ]]; then
  shift || true
  # Re-render pages/decisions.js and decisions/INDEX.md from decisions/*.md.
  # Pass `check` to fail instead of writing, which is what CI and
  # tests/test_doc_claims.py do. The decision documents are the authored source;
  # both outputs are generated and carry a do-not-edit banner.
  exec "$PYTHON_BIN" tools/decisions.py "${1:-build}"
fi

# Fall through: pass-through to the gain-curve driver for any other CL-Bench
# task / SUT (it is SUT-agnostic; see `--help` and `--list-tasks`).
exec "$PYTHON_BIN" -m retention_bench.gain_curve "$@"
