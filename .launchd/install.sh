#!/bin/bash
# Install the auto-push LaunchAgent. Run once.
#
# Usage:
#   cd ~/AI-Developer-Ecosystem && ./.launchd/install.sh
#
# After installing, every 5 minutes macOS will execute .push-pending.sh
# in the background. Logs go to .session-pending/launchd.{out,err}.log
# and the script's own log .session-pending/push.log
#
# To uninstall:
#   launchctl unload ~/Library/LaunchAgents/com.depoli.ai-dev-push.plist
#   rm ~/Library/LaunchAgents/com.depoli.ai-dev-push.plist

set -e

SRC="/Users/paolodeidda/AI-Developer-Ecosystem/.launchd/com.depoli.ai-dev-push.plist"
DEST_DIR="$HOME/Library/LaunchAgents"
DEST="$DEST_DIR/com.depoli.ai-dev-push.plist"

mkdir -p "$DEST_DIR"

# Unload any previous version first (ignore errors on first install).
launchctl unload "$DEST" 2>/dev/null || true

cp "$SRC" "$DEST"
launchctl load "$DEST"

echo "Installed. Status:"
launchctl list | grep com.depoli.ai-dev-push || echo "  (not yet visible, will appear after first run)"
echo ""
echo "Next run will happen within 5 minutes. Tail the logs with:"
echo "  tail -f ~/AI-Developer-Ecosystem/.session-pending/push.log"
