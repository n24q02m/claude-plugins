#!/bin/bash
# Test for better-code-review-graph session-start.sh hook
set -euo pipefail

# Calculate the path to the hook script relative to this test file
HOOK_SCRIPTPING="$(cd "$(dirname "$0")"/.. && pwd)"
HOOK_SCRIPT="$HOOK_SCRIPTPING/session-start.sh"
PASS=0
FAIL=0

assert_contains() {
  local desc="$1" expected="$2" actual="$3"
  if echo "$actual" | grep -qF "$expected"; then
    echo "PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $desc"
    echo "  Expected to contain: $expected"
    echo "  Actual: $actual"
    FAIL=$((FAIL + 1))
  fi
}

# Test in temporary directory
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

# Test 1: No database file
output=$(bash "$HOOK_SCRIPT")
assert_contains "no DB shows build guidance" "No knowledge graph found" "$output"

# Test 2: Database file exists
mkdir -p .code-review-graph
touch .code-review-graph/graph.db
output=$(bash "$HOOK_SCRIPT")
assert_contains "existing DB shows available message" "Knowledge graph is available" "$output"
assert_contains "existing DB mentions semantic_search" "semantic_search_nodes_tool" "$output"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
