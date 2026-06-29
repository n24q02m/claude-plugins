#!/usr/bin/env bash
# UserPromptSubmit hook -- pre-warm wet-mcp docs cache when the user prompt
# mentions a known Tier 1 library import.
#
# Spec section 12.2 NICE + Phase 3 plan task 10. Best-effort only;
# never blocks the prompt and exits 0 on any error.
#
# How it works:
#   1. Read the user prompt from $CLAUDE_USER_PROMPT (or stdin).
#   2. Extract library identifiers from common import keyword patterns
#      (Python, JavaScript/TypeScript, Go).
#   3. For each match that is a Tier 1 library, fire-and-forget a
#      docs_resolve warmup so subsequent docs_query calls hit a fresh
#      OS page-cache for the library chunks.
#
# The hook intentionally does NOT block; the warmup is detached.

set -euo pipefail

PROMPT="${CLAUDE_USER_PROMPT:-}"
if [ -z "$PROMPT" ]; then
    # Some harnesses pipe the prompt on stdin instead.
    if [ -t 0 ]; then
        exit 0
    fi
    PROMPT=$(cat || true)
fi

if [ -z "$PROMPT" ]; then
    exit 0
fi

# Extract candidate identifiers from the prompt and match against Tier 1 list.
# Now using a python script for better maintainability and robustness.
UNIQUE_HITS=$(printf "%s" "$PROMPT" | python3 "$(dirname "$0")/extract_prewarm_libraries.py")

if [ -z "$UNIQUE_HITS" ]; then
    exit 0
fi

# Fire-and-forget docs_resolve warmup. We use the wet-mcp CLI in
# headless mode if available; otherwise log to stderr and exit so the
# operator can see what would have warmed.
WARMUP_LOG="${WET_PREWARM_LOG:-/dev/null}"
if command -v wet-mcp >/dev/null 2>&1; then
    while IFS= read -r lib; do
        [ -z "$lib" ] && continue
        # Detached subshell -- never blocks the user prompt.
        (
            wet-mcp call --tool search --action docs_resolve \
                --query "$lib" >>"$WARMUP_LOG" 2>&1 || true
        ) &
    done <<< "$UNIQUE_HITS"
else
    # Advisory-only fallback: tell the operator which libraries would
    # have been warmed if the wet-mcp CLI were on PATH.
    {
        printf "[wet-mcp UserPromptSubmit hook] would prewarm: "
        # Use awk to join UNIQUE_HITS by space for the advisory log
        printf "%s" "$UNIQUE_HITS" | awk "{printf \"%s \", \$0} END {printf \"\n\"}"
    } >&2
fi

exit 0
