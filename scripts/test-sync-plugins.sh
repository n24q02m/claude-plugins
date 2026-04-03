#!/bin/bash
set -euo pipefail

# Source the script to test its functions
# We need to mock some variables first
export REPOS_DIR="/tmp/repos"
export ROOT="/tmp/root"

# Setup mock environment
setup_env() {
  rm -rf "$REPOS_DIR" "$ROOT"
  mkdir -p "$REPOS_DIR/repo1/.claude-plugin"
  mkdir -p "$REPOS_DIR/repo1/skills"
  echo '{"name": "repo1"}' > "$REPOS_DIR/repo1/.claude-plugin/plugin.json"
  echo 'skill1' > "$REPOS_DIR/repo1/skills/skill1.md"

  # repo2 is missing

  mkdir -p "$REPOS_DIR/repo3/.claude-plugin"
  echo '{"name": "repo3"}' > "$REPOS_DIR/repo3/.claude-plugin/plugin.json"

  # repo4 has NO plugin.json but HAS skills
  mkdir -p "$REPOS_DIR/repo4/skills"
  echo 'skill4' > "$REPOS_DIR/repo4/skills/skill4.md"

  # repo5 has gemini-extension.json
  mkdir -p "$REPOS_DIR/repo5/.claude-plugin"
  echo '{"name": "repo5"}' > "$REPOS_DIR/repo5/.claude-plugin/plugin.json"
  echo '{"version": "1.0.0"}' > "$REPOS_DIR/repo5/gemini-extension.json"
}

# Source the script but don't execute sync_plugins automatically
source "$(dirname "$0")/sync-plugins.sh"

# Test has_files
test_has_files() {
  echo "Testing has_files..."
  local test_base="/tmp/test_dir"
  rm -rf "$test_base"
  mkdir -p "$test_base/empty"
  mkdir -p "$test_base/non_empty"
  touch "$test_base/non_empty/file"

  if has_files "$test_base/empty"; then
    echo "FAIL: empty dir reported as having files"
    return 1
  fi

  if ! has_files "$test_base/non_empty"; then
    echo "FAIL: non-empty dir reported as NOT having files"
    return 1
  fi
  echo "PASS: has_files"
}

# Test sync_plugins with missing source
test_sync_missing_source() {
  echo "Testing sync_plugins with missing source and various repo structures..."
  setup_env
  # Override PLUGINS for testing
  PLUGINS=("repo1" "repo2" "repo3" "repo4" "repo5")

  # Ensure destination root exists but repo dirs don't
  mkdir -p "$ROOT/plugins"

  # Run sync_plugins and capture output
  local output
  output=$(sync_plugins 2>&1)

  if [[ ! "$output" =~ "OK repo1" ]]; then
    echo "FAIL: repo1 should have been synced"
    echo "Output: $output"
    return 1
  fi

  if [[ ! "$output" =~ "SKIP repo2 (not found at /tmp/repos/repo2)" ]]; then
    echo "FAIL: repo2 should have been skipped"
    echo "Output: $output"
    return 1
  fi

  if [[ ! "$output" =~ "OK repo3" ]]; then
    echo "FAIL: repo3 should have been synced"
    echo "Output: $output"
    return 1
  fi

  if [[ ! "$output" =~ "OK repo4" ]]; then
    echo "FAIL: repo4 should have been synced"
    echo "Output: $output"
    return 1
  fi

  if [[ ! "$output" =~ "OK repo5" ]]; then
    echo "FAIL: repo5 should have been synced"
    echo "Output: $output"
    return 1
  fi

  if [ ! -f "$ROOT/plugins/repo1/.claude-plugin/plugin.json" ]; then
    echo "FAIL: repo1 plugin.json missing"
    return 1
  fi

  if [ ! -d "$ROOT/plugins/repo4/skills" ]; then
    echo "FAIL: repo4 skills missing"
    return 1
  fi

  if [ ! -f "$ROOT/plugins/repo5/gemini-extension.json" ]; then
    echo "FAIL: repo5 gemini-extension.json missing"
    return 1
  fi

  echo "PASS: sync_plugins handles complex scenarios"
}

run_tests() {
  test_has_files || return 1
  test_sync_missing_source || return 1
  echo "All tests passed!"
}

run_tests
