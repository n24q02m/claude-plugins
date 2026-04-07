#!/bin/bash
set -euo pipefail

# Setup mock environment
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

REPOS="$TMP/repos"
ROOT="$TMP/root"
mkdir -p "$REPOS/only-skills/skills/demo"
touch "$REPOS/only-skills/skills/demo/SKILL.md"

# We need to source it to run sync_plugins
source scripts/sync-plugins.sh

# Override globals AFTER sourcing
REPOS_DIR="$REPOS"
ROOT="$ROOT"
PLUGINS=(only-skills)

echo "Running sync_plugins for only-skills..."
if sync_plugins; then
  echo "SUCCESS: sync_plugins completed"
else
  echo "FAILURE: sync_plugins failed"
fi

if [ -d "$ROOT/plugins/only-skills/skills" ]; then
  echo "PASS: skills synced"
else
  echo "FAIL: skills NOT synced"
fi
