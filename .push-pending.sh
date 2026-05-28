#!/bin/bash
# Push the pending autonomous-session commits to GitHub.
#
# Why this script exists:
#   The autonomous Cowork sandbox does not carry GitHub credentials, so it
#   cannot `git push` directly. It instead writes a git bundle to
#   `.session-pending/` (gitignored) containing the new commits, and leaves
#   this script for the host to fetch and push from.
#
# Designed to run unattended from a LaunchAgent every few minutes. It is
# safe to run on a clean tree (no-op) and safe to re-run after a partial
# failure (idempotent: bundles already on origin are skipped).
#
# Manual usage:   ./.push-pending.sh
# Automatic:      see .launchd/com.depoli.ai-dev-push.plist

set -u
set -o pipefail

MAIN="/Users/paolodeidda/AI-Developer-Ecosystem"
PENDING="$MAIN/.session-pending"
LOGFILE="$MAIN/.session-pending/push.log"

mkdir -p "$PENDING"
exec >>"$LOGFILE" 2>&1
echo ""
echo "=== $(date '+%Y-%m-%d %H:%M:%S') push-pending run ==="

cd "$MAIN" || { echo "ERROR: cannot cd to $MAIN"; exit 1; }

# 0. Remove stale index.lock if no git process actually owns it.
if [ -f .git/index.lock ]; then
  if pgrep -f "git.*$MAIN" >/dev/null 2>&1; then
    echo "index.lock present and git process running; backing off."
    exit 0
  fi
  echo "Removing stale .git/index.lock"
  rm -f .git/index.lock
fi
# Same for shallow / packed-refs locks that sometimes survive crashes.
rm -f .git/shallow.lock .git/packed-refs.lock .git/HEAD.lock 2>/dev/null || true

# 1. Nothing to do if no bundles waiting.
shopt -s nullglob
bundles=("$PENDING"/*.bundle)
if [ ${#bundles[@]} -eq 0 ]; then
  echo "No pending bundles. Exit clean."
  exit 0
fi
echo "Found ${#bundles[@]} bundle(s)."

# 2. Auto-stash any dirty working tree so the script never blocks on it.
DIRTY=""
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  DIRTY="1"
  echo "Working tree dirty; auto-stashing."
  git stash push --include-untracked -m "push-pending auto-stash $(date '+%Y%m%d-%H%M%S')" || {
    echo "WARN: stash failed; continuing anyway"
    DIRTY=""
  }
fi

# Restore stash on exit so the user never loses local edits.
restore_stash() {
  if [ -n "$DIRTY" ]; then
    echo "Restoring auto-stashed changes."
    git stash pop || echo "WARN: could not pop stash; check 'git stash list'"
  fi
}
trap restore_stash EXIT

# 3. Make sure we are on main and up-to-date with origin.
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "Switching from '$CURRENT_BRANCH' to main."
  git checkout main || { echo "ERROR: cannot checkout main"; exit 1; }
fi

git fetch origin --quiet || { echo "ERROR: git fetch failed (offline?)"; exit 0; }

# Reset main to origin/main if local is behind / diverged, so bundles land
# cleanly. Local commits past origin/main are preserved in reflog.
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" != "$REMOTE" ]; then
  if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
    echo "Local behind origin; fast-forwarding."
    git merge --ff-only origin/main
  else
    echo "Local diverged from origin; resetting to origin/main (reflog: $LOCAL)."
    git reset --hard origin/main
  fi
fi

# 4. Apply each bundle in lexicographic order. Skip bundles whose tip is
#    already reachable from HEAD (idempotent re-run after partial push).
applied_any=0
for b in "${bundles[@]}"; do
  echo "Inspecting bundle: $(basename "$b")"
  TIP=$(git bundle list-heads "$b" 2>/dev/null | awk '/refs\/heads\/main$/ {print $1}')
  if [ -z "$TIP" ]; then
    echo "  no main ref in bundle; skipping."
    continue
  fi
  if git merge-base --is-ancestor "$TIP" HEAD 2>/dev/null; then
    echo "  tip $TIP already in main; removing stale bundle."
    rm -f "$b"
    continue
  fi
  echo "  fetching bundle tip $TIP."
  if ! git fetch "$b" main; then
    echo "  WARN: fetch from bundle failed; leaving bundle in place."
    continue
  fi
  if git merge --ff-only FETCH_HEAD; then
    echo "  merged."
    applied_any=1
  else
    echo "  ERROR: ff-only merge failed; leaving bundle for manual review."
    continue
  fi
done

# 5. Push if we have anything ahead of origin.
AHEAD=$(git rev-list --count origin/main..HEAD)
if [ "$AHEAD" -gt 0 ]; then
  echo "Pushing $AHEAD commit(s) to origin/main."
  if git push origin main; then
    echo "Push OK."
  else
    echo "ERROR: push failed; bundles preserved for retry."
    exit 1
  fi
else
  echo "Nothing to push."
fi

# 6. Clean up bundles whose tips are now in origin/main.
git fetch origin --quiet
for b in "${bundles[@]}"; do
  [ -f "$b" ] || continue
  TIP=$(git bundle list-heads "$b" 2>/dev/null | awk '/refs\/heads\/main$/ {print $1}')
  if [ -n "$TIP" ] && git merge-base --is-ancestor "$TIP" origin/main 2>/dev/null; then
    rm -f "$b"
    echo "Cleaned up applied bundle: $(basename "$b")"
  fi
done

echo "Run complete."
