#!/bin/bash
# Push the pending autonomous-session commits to GitHub.
#
# Why this script exists:
#   The autonomous Cowork sandbox does not carry GitHub credentials, so it
#   cannot `git push` directly. It instead writes a git bundle to
#   `.session-pending/` (gitignored) containing the new commits, and leaves
#   this script for the host to fetch and push from.
#
# Run this on your Mac whenever you see `.session-pending/*.bundle` files.
# After a successful push, the bundles are deleted automatically.
set -e

MAIN="/Users/paolodeidda/AI-Developer-Ecosystem"
PENDING="$MAIN/.session-pending"

cd "$MAIN"

# Sanity: clean working tree before we fast-forward.
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "Working tree is dirty. Commit or stash before running this script."
  git status --short
  exit 1
fi

# Sanity: nothing to do if no bundles waiting.
shopt -s nullglob
bundles=("$PENDING"/*.bundle)
if [ ${#bundles[@]} -eq 0 ]; then
  echo "No pending bundles in $PENDING. Nothing to push."
  exit 0
fi

# Make sure we are on main and up-to-date.
git checkout main
git fetch origin

# Apply each bundle in lexicographic order (filenames are ISO dates).
for b in "${bundles[@]}"; do
  echo "Applying bundle: $b"
  git fetch "$b" main
  git merge --ff-only FETCH_HEAD
done

git push origin main

# Clean up applied bundles.
rm -f "${bundles[@]}"
echo "Done. ${#bundles[@]} bundle(s) pushed to origin/main and cleaned up."
