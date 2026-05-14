#!/bin/bash
# Run this once to push today's (2026-05-14) session commit to GitHub.
# The commit is staged in /tmp/ai-dev-fresh — copy it into the main repo and push.
set -e

MAIN="/Users/paolodeidda/AI-Developer-Ecosystem"
TEMP="/tmp/ai-dev-fresh"

if [ ! -d "$TEMP/.git" ]; then
  echo "Temp repo not found at $TEMP. Re-clone and re-apply changes manually."
  exit 1
fi

# Fast-forward the main repo from the temp clone
cd "$MAIN"
git fetch "$TEMP" main
git merge --ff-only FETCH_HEAD
git push origin main

echo "Done. Commit pushed to origin/main."
