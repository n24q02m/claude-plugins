#!/bin/bash
set -euo pipefail

# Path to the script under test
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_UNDER_TEST="${SCRIPT_DIR}/session-start.sh"

# Source the script
source "$SCRIPT_UNDER_TEST"

# Test setup
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT
ORIGINAL_PWD=$(pwd)
cd "$TEST_DIR"

# Test 1: No knowledge graph found
test_no_graph() {
    echo "Running test_no_graph..."
    # Ensure DB_PATH doesn't exist (it shouldn't in a fresh mktemp dir)

    output=$(main 2>&1)
    if [[ "$output" == *"[better-code-review-graph] No knowledge graph found"* ]]; then
        echo "PASS: test_no_graph"
    else
        echo "FAIL: test_no_graph"
        echo "Expected output to contain: [better-code-review-graph] No knowledge graph found"
        echo "Actual output: $output"
        exit 1
    fi
}

# Test 2: Knowledge graph found
test_graph_exists() {
    echo "Running test_graph_exists..."
    mkdir -p ".code-review-graph"
    touch ".code-review-graph/graph.db"

    output=$(main 2>&1)
    if [[ "$output" == *"[better-code-review-graph] Knowledge graph is available"* ]]; then
        echo "PASS: test_graph_exists"
    else
        echo "FAIL: test_graph_exists"
        echo "Expected output to contain: [better-code-review-graph] Knowledge graph is available"
        echo "Actual output: $output"
        exit 1
    fi
}

# Run tests
test_no_graph
test_graph_exists

echo "All tests passed!"
