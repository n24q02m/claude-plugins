#!/usr/bin/env python3
"""PreToolUse hook: hint when better-notion-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
Notion uses OAuth via claude.ai proxy in HTTP mode.
"""
import json
import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mcp_common import is_relay_configured

SERVER_NAME = "better-notion-mcp"
CREDENTIAL_KEYS = ["NOTION_TOKEN"]
EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def _is_configured() -> bool:
    for k in CREDENTIAL_KEYS:
        if os.environ.get(k):
            return True
    return is_relay_configured()


def main() -> None:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            print(json.dumps({
                "decision": "block",
                "reason": "Invalid input: payload must be a JSON dictionary",
            }))
            sys.exit(2)
    except Exception:
        print(json.dumps({
            "decision": "block",
            "reason": "Invalid input: payload must be a JSON dictionary",
        }))
        sys.exit(2)

    tool_name = data.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if _is_configured():
        sys.exit(0)

    # Non-blocking hint: let server handle unconfigured state
    print(json.dumps({
        "message": (
            "better-notion-mcp: credentials not yet configured. "
            "The server will provide setup instructions."
        ),
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
