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
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    home = os.path.expanduser("~")
    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    paths = [p for p in [
        os.path.join(local_app_data, "mcp", "config.enc") if local_app_data else "",
        os.path.join(app_data, "mcp", "Config", "config.enc") if app_data else "",
        os.path.join(home, ".config", "mcp", "config.enc"),
    ] if p]
    for p in paths:
        if os.path.exists(p):
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
