#!/usr/bin/env python3
"""PreToolUse hook: block when better-telegram-mcp credentials are not configured.

Blocking -- Telegram tools cannot function without credentials.
Allows config and help tools through so the user can initiate setup.
"""
import json
import os
import sys

# Add plugins directory to sys.path to import shared utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mcp_utils import is_configured, EXEMPT_SUFFIXES

SERVER_NAME = "better-telegram-mcp"
# Either TELEGRAM_PHONE (user mode) or TELEGRAM_BOT_TOKEN (bot mode) is required.
# TELEGRAM_API_ID / TELEGRAM_API_HASH have built-in defaults and are not checked here.
CREDENTIAL_KEYS = ["TELEGRAM_PHONE", "TELEGRAM_BOT_TOKEN"]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if not is_configured(CREDENTIAL_KEYS):
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
