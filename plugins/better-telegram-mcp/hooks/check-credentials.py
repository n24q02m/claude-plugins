#!/usr/bin/env python3
"""PreToolUse hook: block when better-telegram-mcp credentials are not configured.

Blocking -- Telegram tools cannot function without credentials.
Allows config and help tools through so the user can initiate setup.
"""
import json
import os
import sys

SERVER_NAME = "better-telegram-mcp"
# Either TELEGRAM_PHONE (user mode) or TELEGRAM_BOT_TOKEN (bot mode) is required.
# TELEGRAM_API_ID / TELEGRAM_API_HASH have built-in defaults and are not checked here.
CREDENTIAL_KEYS = ["TELEGRAM_PHONE", "TELEGRAM_BOT_TOKEN"]
# Tools that work without credentials
EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def _is_configured() -> bool:
    # Optimize: explicit for loops avoid generator overhead
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
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    # Optimize: str.endswith accepts a tuple directly which is faster
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if not _is_configured():
        print(json.dumps({
            "decision": "block",
            "reason": (
                "better-telegram-mcp credentials not configured. "
                "Set TELEGRAM_PHONE (user mode) or TELEGRAM_BOT_TOKEN (bot mode) "
                "in your MCP server environment, "
                "or use the config tool with action='status' for setup instructions."
            ),
        }))
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
