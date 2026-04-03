#!/bin/bash
set -euo pipefail

# Setup
TEST_DIR="test_workspace"
mkdir -p "$TEST_DIR/repos/plugin-a/skills"
echo "skill 1" > "$TEST_DIR/repos/plugin-a/skills/skill1.md"
mkdir -p "$TEST_DIR/repos/plugin-a/.claude-plugin"
echo '{"name": "plugin-a"}' > "$TEST_DIR/repos/plugin-a/.claude-plugin/plugin.json"

mkdir -p "$TEST_DIR/repos/plugin-b/hooks"
echo "hook 1" > "$TEST_DIR/repos/plugin-b/hooks/hook1.sh"

export REPOS_DIR="$(pwd)/$TEST_DIR/repos"
export ROOT="$(pwd)/$TEST_DIR/root"
mkdir -p "$ROOT/plugins"

# Create a test script with limited plugins
sed "s/PLUGINS=(.*)/PLUGINS=(plugin-a plugin-b)/" scripts/sync-plugins.sh > "$TEST_DIR/sync-plugins-test.sh"
chmod +x "$TEST_DIR/sync-plugins-test.sh"

# Run sync
REPOS_DIR="$REPOS_DIR" ROOT="$ROOT" bash "$TEST_DIR/sync-plugins-test.sh"

# Assertions
echo "Running assertions..."

test_failed=0

if [ ! -f "$ROOT/plugins/plugin-a/.claude-plugin/plugin.json" ]; then
  echo "FAIL: plugin-a/plugin.json missing"
  test_failed=1
fi

if [ ! -d "$ROOT/plugins/plugin-a/skills" ]; then
  echo "FAIL: plugin-a/skills directory missing"
  test_failed=1
fi

if [ ! -f "$ROOT/plugins/plugin-a/skills/skill1.md" ]; then
  echo "FAIL: plugin-a/skills/skill1.md missing"
  test_failed=1
fi

if [ ! -d "$ROOT/plugins/plugin-b/hooks" ]; then
  echo "FAIL: plugin-b/hooks directory missing"
  test_failed=1
fi

if [ -d "$ROOT/plugins/plugin-b/skills" ]; then
  echo "FAIL: plugin-b should not have skills directory"
  test_failed=1
fi

if [ $test_failed -eq 0 ]; then
  echo "All tests passed!"
else
  echo "Tests failed!"
fi

# Cleanup
# rm -rf "$TEST_DIR"
