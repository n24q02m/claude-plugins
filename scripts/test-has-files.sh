#!/bin/bash
set -euo pipefail

# Source the script to test its functions
# shellcheck source=scripts/sync-plugins.sh
source "$(dirname "$0")/sync-plugins.sh"

assert_true() {
  if "$@"; then
    echo "PASS: $*"
  else
    echo "FAIL: $*"
    return 1
  fi
}

assert_false() {
  if ! "$@"; then
    echo "PASS: ! $*"
  else
    echo "FAIL: ! $*"
    return 1
  fi
}

# Setup temporary test directory
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

echo "Running tests for has_files..."

# Test empty directory
EMPTY_DIR="$TEST_DIR/empty"
mkdir "$EMPTY_DIR"
assert_false has_files "$EMPTY_DIR"

# Test directory with one file
ONE_FILE_DIR="$TEST_DIR/one_file"
mkdir "$ONE_FILE_DIR"
touch "$ONE_FILE_DIR/file.txt"
assert_true has_files "$ONE_FILE_DIR"

# Test directory with multiple files
MULTI_FILE_DIR="$TEST_DIR/multi_file"
mkdir "$MULTI_FILE_DIR"
touch "$MULTI_FILE_DIR/file1.txt" "$MULTI_FILE_DIR/file2.txt"
assert_true has_files "$MULTI_FILE_DIR"

# Test directory with only hidden files
HIDDEN_FILE_DIR="$TEST_DIR/hidden_file"
mkdir "$HIDDEN_FILE_DIR"
touch "$HIDDEN_FILE_DIR/.hidden"
assert_true has_files "$HIDDEN_FILE_DIR"

# Test directory with only a subdirectory
SUBDIR_DIR="$TEST_DIR/subdir"
mkdir -p "$SUBDIR_DIR/sub"
assert_true has_files "$SUBDIR_DIR"

echo "All tests passed!"
