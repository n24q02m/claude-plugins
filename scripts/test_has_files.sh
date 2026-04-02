#!/bin/bash
set -euo pipefail

has_files() {
  local dir="$1"
  shopt -s nullglob dotglob
  for _ in "$dir"/*; do
    shopt -u nullglob dotglob
    return 0
  done
  shopt -u nullglob dotglob
  return 1
}

test_implementation() {
  local func="$1"
  echo "Testing $func..."

  local test_dir
  test_dir=$(mktemp -d)

  # Case 1: Empty directory
  if $func "$test_dir"; then
    echo "  FAIL: Empty directory should return false"
    rm -rf "$test_dir"
    return 1
  fi
  echo "  PASS: Empty directory"

  # Case 2: One file
  touch "$test_dir/file1"
  if ! $func "$test_dir"; then
    echo "  FAIL: Directory with one file should return true"
    rm -rf "$test_dir"
    return 1
  fi
  echo "  PASS: One file"

  # Case 3: Hidden file
  rm -rf "$test_dir"/*
  touch "$test_dir/.hidden"
  if ! $func "$test_dir"; then
    echo "  FAIL: Directory with hidden file should return true"
    rm -rf "$test_dir"
    return 1
  fi
  echo "  PASS: Hidden file"

  # Case 4: Multiple files
  touch "$test_dir/file2" "$test_dir/file3"
  if ! $func "$test_dir"; then
    echo "  FAIL: Directory with multiple files should return true"
    rm -rf "$test_dir"
    return 1
  fi
  echo "  PASS: Multiple files"

  echo "All tests passed for $func"
  rm -rf "$test_dir"
  return 0
}

test_implementation "has_files" || echo "has_files FAILED"
