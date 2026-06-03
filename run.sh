#!/usr/bin/env bash
# retention-bench convenience wrapper.
#
# Usage:
#   ./run.sh smoke                       # canonical MVP smoke run
#   ./run.sh <task.yaml> [harness args]  # arbitrary task; pass-through
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
  task="tasks/smoke-test/task.yaml"
  sut="suts/no_state"

  # Harness prints the run-dir as its last stdout line; capture it so we
  # can hand it straight to the scorer without a manual copy-paste.
  run_dir="$(python3 -m harness "$task" --sut "$sut" "$@" | tee /dev/stderr | tail -n 1)"

  if [[ ! -d "$run_dir" ]]; then
    echo "smoke: harness did not produce a usable run directory: $run_dir" >&2
    exit 1
  fi

  echo ""
  echo "=== Scoring $run_dir ==="
  python3 -m scorer "$run_dir"
  exit 0
fi

# Fall through: pass-through to the harness for any other task.
exec python3 -m harness "$@"
