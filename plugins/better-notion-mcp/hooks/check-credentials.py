#!/usr/bin/env python3
"""PreToolUse hook: hint when better-notion-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
Notion uses OAuth via claude.ai proxy in HTTP mode.
"""
import json
import os
import sys

SERVER_NAME = "better-notion-mcp"
CREDENTIAL_KEYS = ["NOTION_TOKEN"]


def _is_configured() -> bool:
    for k in CREDENTIAL_KEYS:
        if os.environ.get(k):
            return True
    home = os.path.expanduser("~")
    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    # Check common paths directly to avoid list allocations and joins
    path = os.environ.get("LOCALAPPDATA")
    if path and os.path.exists(os.path.join(path, "mcp", "config.enc")):
        return True

    path = os.environ.get("APPDATA")
    if path and os.path.exists(os.path.join(path, "mcp", "Config", "config.enc")):
        return True

    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True

    return False


def main() -> None:
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
