#!/bin/bash
set -euo pipefail

# Path to the script under test
# We use an absolute path to the hook script
HOOK_SCRIPT="$(pwd)/plugins/better-code-review-graph/hooks/session-start.sh"

# Create a temporary test directory
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

cd "$TEST_DIR"

echo "Running tests in $TEST_DIR"

# Test Case 1: Database file missing
echo "Test Case 1: Database file missing"
OUTPUT=$(bash "$HOOK_SCRIPT")
EXPECTED="[better-code-review-graph] No knowledge graph found. Use the graph tool with action='build' to parse this codebase and enable graph-powered queries."

if [[ "$OUTPUT" != "$EXPECTED" ]]; then
    echo "FAILED: Expected output for missing DB did not match."
    echo "Expected: $EXPECTED"
    echo "Actual: $OUTPUT"
    false
fi
echo "PASSED: Test Case 1"

# Test Case 2: Database file exists
echo "Test Case 2: Database file exists"
mkdir -p .code-review-graph
touch .code-review-graph/graph.db

OUTPUT=$(bash "$HOOK_SCRIPT")

if [[ ! "$OUTPUT" =~ "[better-code-review-graph] Knowledge graph is available." ]]; then
    echo "FAILED: Expected output for existing DB did not match."
    echo "Actual: $OUTPUT"
    false
fi
echo "PASSED: Test Case 2"

echo "All tests passed successfully!"
