#!/usr/bin/env bash
#
# promote.sh — snapshot the public subset of `dev` onto the orphan `main`.
#
# `main` is an ORPHAN branch (no shared history with `dev`), so the mess on
# `dev` is structurally unreachable from `main`'s `git log`. Promotion is a
# SNAPSHOT, never a merge: we clear the target tree and re-extract exactly the
# paths in PUBLIC_PATHS from the source ref. Clearing first means deletions on
# `dev` propagate (a plain `git checkout dev -- <path>` would never remove a
# file). `main` ends as a strict path-subset of `dev` — no special-cased files.
#
# Usage:
#   scripts/promote.sh dryrun           # orphan-snapshot into a throwaway branch,
#                                        # verify no dev-only paths leaked, report,
#                                        # then delete the throwaway branch.
#   scripts/promote.sh cut [--force]     # create the real orphan `main` (first
#                                        # release). Refuses if `main` exists
#                                        # unless --force (which replaces it).
#   scripts/promote.sh release           # add a new snapshot commit onto an
#                                        # existing `main` (subsequent releases).
#
#   SRC=dev scripts/promote.sh ...       # override the source ref (default: dev).
#
# The script never pushes and never flips repo visibility — that's a human step.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

SRC="${SRC:-dev}"
MANIFEST="$REPO_ROOT/PUBLIC_PATHS"
MODE="${1:-}"
FORCE="${2:-}"

[ -f "$MANIFEST" ] || { echo "error: $MANIFEST not found" >&2; exit 1; }
git rev-parse --verify --quiet "$SRC" >/dev/null \
  || { echo "error: source ref '$SRC' does not exist" >&2; exit 1; }

# Parse PUBLIC_PATHS into INCLUDES / EXCLUDES (strip inline comments + blanks).
INCLUDES=(); EXCLUDES=()
while IFS= read -r raw; do
  line="${raw%%#*}"; line="$(echo "$line" | xargs)"   # strip comment + trim
  [ -z "$line" ] && continue
  if [[ "$line" == \!* ]]; then EXCLUDES+=("${line#\!}"); else INCLUDES+=("$line"); fi
done < "$MANIFEST"

# Restore the caller's branch on exit (the script hops branches). Force-checkout
# is deliberate: snapshot work is throwaway, and everything real lives in commits.
START_BRANCH="$(git symbolic-ref --quiet --short HEAD || echo '')"
restore() { [ -n "$START_BRANCH" ] && git checkout -f -q "$START_BRANCH"; }

# Extract the whitelist from $SRC onto the *current* branch.
# Assumes the index/worktree has already been cleared of tracked files.
extract_whitelist() {
  local p
  for p in "${INCLUDES[@]}"; do
    if [ -n "$(git ls-tree -r --name-only "$SRC" -- "$p")" ]; then
      git checkout "$SRC" -- "$p"
    else
      echo "  (skip missing on $SRC: $p)"
    fi
  done
  for e in "${EXCLUDES[@]}"; do
    git rm -rfq --ignore-unmatch --cached "$e" >/dev/null 2>&1 || true
    rm -rf "$e"
  done
  git add -A
}

# Verify the staged tree contains NO known dev-only path. Returns nonzero on leak.
verify_no_leak() {
  local leak
  leak="$(git ls-files | grep -E '^(feedback/|history/|scratch/|\.tasks/|TASKS\.md|AGENTS\.md|scripts/|PUBLIC_PATHS|RELEASING\.md|docs/archive/)' || true)"
  if [ -n "$leak" ]; then
    echo "LEAK — dev-only paths present in snapshot:" >&2
    echo "$leak" | sed 's/^/  /' >&2
    return 1
  fi
}

build_orphan() {  # $1 = target branch name
  local target="$1"
  git checkout -q --orphan "$target"
  git rm -rfq --ignore-unmatch . >/dev/null 2>&1 || true   # clear index + worktree
  extract_whitelist
}

case "$MODE" in
  dryrun)
    git branch -D main-dryrun >/dev/null 2>&1 || true
    build_orphan main-dryrun
    echo "=== snapshot tree (main-dryrun, from $SRC) ==="
    git ls-files | sed 's/^/  /'
    echo "=== leak check ==="
    LEAK_RC=0; verify_no_leak || LEAK_RC=1
    [ "$LEAK_RC" = 0 ] && echo "  OK — no dev-only paths leaked."
    # Tear down: force back to the caller's branch; the unborn orphan is abandoned.
    restore
    git branch -D main-dryrun >/dev/null 2>&1 || true
    echo "=== dry run complete; back on '$START_BRANCH' ==="
    exit $LEAK_RC
    ;;

  cut)
    if git rev-parse --verify --quiet main >/dev/null; then
      [ "$FORCE" = "--force" ] || { echo "error: 'main' exists; pass --force to replace it as a fresh orphan" >&2; exit 1; }
      git branch -D main
    fi
    build_orphan main
    if ! verify_no_leak; then echo "aborting cut" >&2; exit 1; fi
    git commit -q -m "release: retention-bench public snapshot from ${SRC}"
    echo "=== orphan 'main' created; tree: ==="
    git ls-files | sed 's/^/  /'
    echo "=== review, then push manually when ready (this script does not push) ==="
    ;;

  release)
    git rev-parse --verify --quiet main >/dev/null \
      || { echo "error: 'main' does not exist; run 'cut' for the first release" >&2; exit 1; }
    git checkout -q main
    git rm -rfq --ignore-unmatch . >/dev/null 2>&1 || true
    extract_whitelist
    if ! verify_no_leak; then echo "aborting release" >&2; restore; exit 1; fi
    if git diff --cached --quiet; then
      echo "no changes to promote."
    else
      git commit -q -m "release: retention-bench public snapshot from ${SRC}"
      echo "=== new snapshot commit on 'main'; review then push manually ==="
    fi
    ;;

  *)
    echo "usage: scripts/promote.sh {dryrun|cut [--force]|release}" >&2
    exit 2
    ;;
esac
