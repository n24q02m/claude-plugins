#!/bin/bash
# Test for has_files function in scripts/sync-plugins.sh
set -euo pipefail

# Source the script to test its functions
# It's safe because of the [[ "${BASH_SOURCE[0]}" == "${0}" ]] check
source "$(dirname "$0")/sync-plugins.sh"

test_has_files() {
  local temp_dir
  temp_dir=$(mktemp -d)
  trap 'rm -rf "$temp_dir"' RETURN

  echo "Running tests for has_files..."

  # Test 1: Empty directory
  if has_files "$temp_dir"; then
    echo "FAIL: Empty directory reported as having files"
    return 1
  else
    echo "PASS: Empty directory correctly reported as empty"
  fi

  # Test 2: Directory with a regular file
  touch "$temp_dir/file.txt"
  if has_files "$temp_dir"; then
    echo "PASS: Directory with a file correctly reported as having files"
  else
    echo "FAIL: Directory with a file reported as empty"
    return 1
  fi

  # Test 3: Directory with only hidden file
  rm -f "$temp_dir/file.txt"
  touch "$temp_dir/.hidden"
  if has_files "$temp_dir"; then
    echo "PASS: Directory with only a hidden file correctly reported as having files"
  else
    echo "FAIL: Directory with only a hidden file reported as empty"
    return 1
  fi

  # Test 4: Non-existent directory
  if has_files "/tmp/non-existent-$(date +%s)"; then
    echo "FAIL: Non-existent directory reported as having files"
    return 1
  else
    echo "PASS: Non-existent directory correctly reported as empty"
  fi

  echo "All tests for has_files passed!"
  return 0
}

test_has_files
