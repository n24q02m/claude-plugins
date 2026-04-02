#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
# Use a temporary directory for tests
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

# Source the script for testing
# shellcheck source=scripts/sync-plugins.sh
source "$SCRIPT_DIR/sync-plugins.sh"

# Mock variables
export REPOS_DIR="$TEST_DIR/repos"
export ROOT="$TEST_DIR/workspace"

mkdir -p "$REPOS_DIR"
mkdir -p "$ROOT/plugins"

# Test setup: 1 valid, 1 missing, 1 empty
PLUGINS=(valid-repo missing-repo empty-repo)

mkdir -p "$REPOS_DIR/valid-repo/.claude-plugin"
echo '{"name": "valid"}' > "$REPOS_DIR/valid-repo/.claude-plugin/plugin.json"
mkdir -p "$REPOS_DIR/valid-repo/skills"
echo "skill" > "$REPOS_DIR/valid-repo/skills/skill.md"

mkdir -p "$REPOS_DIR/empty-repo"

echo "Running tests..."
# We need to capture the output but also ensure we can check it
# sync_plugins uses the global PLUGINS array
OUTPUT=$(sync_plugins 2>&1)

# Check results
echo "$OUTPUT"

if ! echo "$OUTPUT" | grep -q "OK valid-repo"; then
  echo "FAIL: valid-repo not OK"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "SKIP missing-repo (not found at $REPOS_DIR/missing-repo)"; then
  echo "FAIL: missing-repo not skipped correctly"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "SKIP empty-repo (empty directory at $REPOS_DIR/empty-repo)"; then
  echo "FAIL: empty-repo not skipped correctly"
  exit 1
fi

if [ ! -f "$ROOT/plugins/valid-repo/.claude-plugin/plugin.json" ]; then
  echo "FAIL: valid-repo files not synced"
  exit 1
fi

echo "All tests passed!"
