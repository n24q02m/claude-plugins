#!/bin/bash
# Tests for sync-plugins.sh functions
set -euo pipefail

source "$(dirname "$0")/sync-plugins.sh"

PASS=0
FAIL=0

assert() {
  local desc="$1"
  shift
  if "$@"; then
    printf "%s\n" "PASS: $desc"
    PASS=$((PASS + 1))
  else
    printf "%s\n" "FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

assert_not() {
  local desc="$1"
  shift
  if ! "$@"; then
    printf "%s\n" "PASS: $desc"
    PASS=$((PASS + 1))
  else
    printf "%s\n" "FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

# --- has_files tests ---

test_has_files() {
  local tmp
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' RETURN

  # Empty directory
  assert_not "empty dir has no files" has_files "$tmp"

  # Directory with a regular file
  touch "$tmp/file.txt"
  assert "dir with file detected" has_files "$tmp"

  # Directory with only hidden file
  rm -f "$tmp/file.txt"
  touch "$tmp/.hidden"
  assert "dir with hidden file detected" has_files "$tmp"

  # Non-existent directory
  assert_not "non-existent dir has no files" has_files "/tmp/nonexistent-$$"
}

# --- sync integration test ---

test_sync_plugins() {
  local tmp
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' RETURN

  # Setup mock source repos
  local repos="$tmp/repos"
  mkdir -p "$repos/test-plugin/.claude-plugin"
  printf "%s\n" '{"name":"test-plugin","description":"test","mcpServers":{}}' > "$repos/test-plugin/.claude-plugin/plugin.json"
  mkdir -p "$repos/test-plugin/skills/demo"
  printf "%b\n" "---\ntitle: demo\n---\nDemo skill content that is long enough to pass validation checks." > "$repos/test-plugin/skills/demo/SKILL.md"
  printf "%s\n" '{"version":"1.0.0"}' > "$repos/test-plugin/gemini-extension.json"
  # Setup mock only-skills repo
  mkdir -p "$repos/only-skills/skills/demo"
  printf "%s\n" "demo skill" > "$repos/only-skills/skills/demo/SKILL.md"

  # Setup mock missing repo
  # (test-missing does not exist)

  # Override globals
  local old_plugins=("${PLUGINS[@]}")
  local old_repos_dir="$REPOS_DIR"
  local old_root="$ROOT"
  PLUGINS=("test-plugin" "test-missing" "only-skills")
  REPOS_DIR="$repos"
  ROOT="$tmp/root"
  mkdir -p "$ROOT/plugins"

  # Run sync
  local output
  output=$(sync_plugins 2>&1)

  # Assertions
  assert "plugin.json synced" test -f "$ROOT/plugins/test-plugin/.claude-plugin/plugin.json"
  assert "gemini-extension.json synced" test -f "$ROOT/plugins/test-plugin/gemini-extension.json"
  assert "skills synced" test -d "$ROOT/plugins/test-plugin/skills"
  assert "only-skills synced" test -d "$ROOT/plugins/only-skills/skills"
  if printf "%s\n" "$output" | grep -q "SKIP test-missing"; then
    printf "%s\n" "PASS: missing repo skipped"
    PASS=$((PASS + 1))
  else
    printf "%s\n" "FAIL: missing repo skipped"
    FAIL=$((FAIL + 1))
  fi

  # Restore globals
  PLUGINS=("${old_plugins[@]}")
  REPOS_DIR="$old_repos_dir"
  ROOT="$old_root"
}

# --- sync error path test ---

test_sync_errors() {
  local tmp
  tmp=$(mktemp -d)
  trap 'chmod 755 "$tmp/root" 2>/dev/null || true; rm -rf "$tmp"' RETURN

  # Setup mock source repo
  local repos="$tmp/repos"
  mkdir -p "$repos/test-plugin"
  touch "$repos/test-plugin/gemini-extension.json"

  # Setup read-only root to trigger permission error
  local root="$tmp/root"
  mkdir -p "$root"
  chmod 555 "$root"

  # Override globals
  local old_plugins=("${PLUGINS[@]}")
  local old_repos_dir="$REPOS_DIR"
  local old_root="$ROOT"
  PLUGINS=("test-plugin")
  REPOS_DIR="$repos"
  ROOT="$root"

  # Run sync in a fresh bash process to ensure 'set -e' properly terminates
  # execution on error, which a subshell in the same process might not do
  # depending on how it's called and the bash version.
  if REPOS_DIR="$REPOS_DIR" ROOT="$ROOT" \
     bash -e -c 'source scripts/sync-plugins.sh; PLUGINS=("test-plugin"); sync_plugins' > /dev/null 2>&1; then
    printf "%s\n" "FAIL: sync_plugins should have failed with read-only root"
    FAIL=$((FAIL + 1))
  else
    printf "%s\n" "PASS: sync_plugins failed as expected with read-only root"
    PASS=$((PASS + 1))
  fi

  # Restore globals
  PLUGINS=("${old_plugins[@]}")
  REPOS_DIR="$old_repos_dir"
  ROOT="$old_root"
}

printf "%s\n" "=== has_files tests ==="
test_has_files

printf "%s\n" ""
printf "%s\n" "=== sync_plugins integration test ==="
test_sync_plugins

printf "%s\n" ""
printf "%s\n" "=== sync_plugins error path test ==="
test_sync_errors

printf "%s\n" ""
printf "%s\n" "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
