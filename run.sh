#!/usr/bin/env bash
# Thin wrapper around `python -m harness`.
# Usage: ./run.sh <task-definition.yaml> [--sut <cmd>] [--runs-dir runs] [--keep-dir]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

exec python3 -m harness "$@"
