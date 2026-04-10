#!/bin/bash
set -euo pipefail

# Get absolute path to the hook script
HOOK_SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/check-credentials.py"
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

assert_not_contains() {
  local desc="$1" unexpected="$2" actual="$3"
  if ! echo "$actual" | grep -qF "$unexpected"; then
    echo "PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $desc"
    echo "  Expected NOT to contain: $unexpected"
    echo "  Actual: $actual"
    FAIL=$((FAIL + 1))
  fi
}

# Test in temporary directory
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

HINT="wet-mcp cloud credentials not configured"

# Test 1: No credentials
# Use a clean environment
output=$(env -i HOME="$tmp/empty-home" PATH="$PATH" python3 "$HOOK_SCRIPT" <<EOF
{"tool_name": "wet__some_tool"}
EOF
)
assert_contains "no credentials shows hint" "$HINT" "$output"

# Test 2: Environment variables
output=$(env -i JINA_AI_API_KEY="test-key" HOME="$tmp/empty-home" PATH="$PATH" python3 "$HOOK_SCRIPT" <<EOF
{"tool_name": "wet__some_tool"}
EOF
)
assert_not_contains "env var JINA_AI_API_KEY suppresses hint" "$HINT" "$output"

# Test 3: Config file (LOCALAPPDATA)
mkdir -p "$tmp/local/mcp"
touch "$tmp/local/mcp/config.enc"
output=$(env -i LOCALAPPDATA="$tmp/local" HOME="$tmp/empty-home" PATH="$PATH" python3 "$HOOK_SCRIPT" <<EOF
{"tool_name": "wet__some_tool"}
EOF
)
assert_not_contains "LOCALAPPDATA config suppresses hint" "$HINT" "$output"

# Use a different tmp subdir for each config test to avoid interference

# Test 4: Config file (APPDATA)
mkdir -p "$tmp/appdata/mcp/Config"
touch "$tmp/appdata/mcp/Config/config.enc"
output=$(env -i APPDATA="$tmp/appdata" HOME="$tmp/empty-home" PATH="$PATH" python3 "$HOOK_SCRIPT" <<EOF
{"tool_name": "wet__some_tool"}
EOF
)
assert_not_contains "APPDATA config suppresses hint" "$HINT" "$output"

# Test 5: Config file (HOME)
mkdir -p "$tmp/home/.config/mcp"
touch "$tmp/home/.config/mcp/config.enc"
output=$(env -i HOME="$tmp/home" PATH="$PATH" python3 "$HOOK_SCRIPT" <<EOF
{"tool_name": "wet__some_tool"}
EOF
)
assert_not_contains "HOME config suppresses hint" "$HINT" "$output"

# Test 6: Exempt tools
output=$(env -i HOME="$tmp/empty-home" PATH="$PATH" python3 "$HOOK_SCRIPT" <<EOF
{"tool_name": "wet__setup"}
EOF
)
assert_not_contains "exempt tool wet__setup suppresses hint" "$HINT" "$output"

# Test 7: Invalid input
output=$(echo "" | env -i HOME="$tmp/empty-home" PATH="$PATH" python3 "$HOOK_SCRIPT" 2>&1)
assert_not_contains "invalid input exits silently" "$HINT" "$output"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
