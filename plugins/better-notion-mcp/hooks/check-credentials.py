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
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data and os.path.exists(os.path.join(local_app_data, "mcp", "config.enc")):
        return True
    app_data = os.environ.get("APPDATA")
    if app_data and os.path.exists(os.path.join(app_data, "mcp", "Config", "config.enc")):
        return True
    home = os.path.expanduser("~")
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
