#!/usr/bin/env bash
#
# promote.sh — snapshot the public subset of `dev` onto the orphan `main`.
#
# `main` is an ORPHAN branch (no shared history with `dev`), so the mess on
# `dev` is structurally unreachable from `main`'s `git log`. Promotion is a
# SNAPSHOT, never a merge: we build the target tree from exactly the paths in
# PUBLIC_PATHS, read from the SOURCE REF's committed tree. `main` ends as a
# strict path-subset of `dev` — no special-cased files.
#
# All work happens in a THROWAWAY temporary git worktree. The caller's working
# tree (`/workspace`) is NEVER touched — uncommitted edits and untracked files
# (e.g. an in-progress outreach draft, runs/) are completely safe. We also only
# ever read the source ref's *committed* tree, so untracked files cannot leak in.
#
# Usage:
#   scripts/promote.sh dryrun           # snapshot into a temp worktree, verify no
#                                        # dev-only paths leaked, report, discard.
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

WT=""
cleanup() { [ -n "$WT" ] && [ -d "$WT" ] && git worktree remove --force "$WT" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# Build the public snapshot in the temp worktree $WT (already an empty index on
# the desired target branch). Reads only $SRC's committed tree — no `git add -A`,
# so nothing untracked can ever enter the snapshot.
build_snapshot() {
  local p e
  for p in "${INCLUDES[@]}"; do
    if [ -n "$(git -C "$WT" ls-tree -r --name-only "$SRC" -- "$p")" ]; then
      git -C "$WT" checkout "$SRC" -- "$p"
    else
      echo "  (skip missing on $SRC: $p)"
    fi
  done
  for e in "${EXCLUDES[@]}"; do
    git -C "$WT" rm -rfq --ignore-unmatch --cached "$e" >/dev/null 2>&1 || true
    rm -rf "${WT:?}/$e"
  done
}

# Fail (nonzero) if the staged tree in $WT contains any known dev-only path.
verify_no_leak() {
  local leak
  leak="$(git -C "$WT" ls-files | grep -E '^(feedback/|history/|scratch/|\.tasks/|TASKS\.md|AGENTS\.md|scripts/|PUBLIC_PATHS|RELEASING\.md|docs/archive/)' || true)"
  if [ -n "$leak" ]; then
    echo "LEAK — dev-only paths present in snapshot:" >&2
    echo "$leak" | sed 's/^/  /' >&2
    return 1
  fi
}

new_worktree_orphan() {  # $1 = orphan branch name; create temp WT with empty index on it
  WT="$(mktemp -d)"
  git worktree add -q --detach "$WT" "$SRC"
  git -C "$WT" checkout -q --orphan "$1"
  git -C "$WT" rm -rfq --ignore-unmatch . >/dev/null 2>&1 || true
}

case "$MODE" in
  dryrun)
    new_worktree_orphan _promote_dryrun
    build_snapshot
    echo "=== snapshot tree (from $SRC) ==="
    git -C "$WT" ls-files | sed 's/^/  /'
    echo "=== leak check ==="
    if verify_no_leak; then echo "  OK — no dev-only paths leaked."; RC=0; else RC=1; fi
    echo "=== dry run complete; temp worktree discarded, caller tree untouched ==="
    exit $RC
    ;;

  cut)
    if git rev-parse --verify --quiet main >/dev/null; then
      [ "$FORCE" = "--force" ] || { echo "error: 'main' exists; pass --force to replace it as a fresh orphan" >&2; exit 1; }
      git worktree list --porcelain | grep -q 'branch refs/heads/main$' \
        && { echo "error: 'main' is checked out in a worktree; remove it first" >&2; exit 1; }
      git branch -D main
    fi
    new_worktree_orphan main
    build_snapshot
    verify_no_leak || { echo "aborting cut" >&2; exit 1; }
    git -C "$WT" commit -q -m "release: retention-bench public snapshot from ${SRC}"
    echo "=== orphan 'main' created; tree: ==="
    git -C "$WT" ls-files | sed 's/^/  /'
    echo "=== review (git log main / git ls-tree -r main), then push manually ==="
    ;;

  release)
    git rev-parse --verify --quiet main >/dev/null \
      || { echo "error: 'main' does not exist; run 'cut' for the first release" >&2; exit 1; }
    WT="$(mktemp -d)"
    git worktree add -q "$WT" main
    git -C "$WT" rm -rfq --ignore-unmatch . >/dev/null 2>&1 || true
    build_snapshot
    verify_no_leak || { echo "aborting release" >&2; exit 1; }
    if git -C "$WT" diff --cached --quiet; then
      echo "no changes to promote."
    else
      git -C "$WT" commit -q -m "release: retention-bench public snapshot from ${SRC}"
      echo "=== new snapshot commit on 'main'; review then push manually ==="
    fi
    ;;

  *)
    echo "usage: scripts/promote.sh {dryrun|cut [--force]|release}" >&2
    exit 2
    ;;
esac
