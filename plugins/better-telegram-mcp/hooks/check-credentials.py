#!/usr/bin/env python3
"""PreToolUse hook: block when better-telegram-mcp credentials are not configured.

Blocking -- Telegram tools cannot function without credentials.
Allows config and help tools through so the user can initiate setup.
"""
import json
import sys

# Shared utility is injected into the hooks directory during sync
try:
    from mcp_hooks_util import is_configured
except ImportError:
    # Fallback for local development if not in path
    import os
    sys.path.append(os.path.dirname(__file__))
    from mcp_hooks_util import is_configured

SERVER_NAME = "better-telegram-mcp"
# Either TELEGRAM_PHONE (user mode) or TELEGRAM_BOT_TOKEN (bot mode) is required.
CREDENTIAL_KEYS = ["TELEGRAM_PHONE", "TELEGRAM_BOT_TOKEN"]
# Tools that work without credentials
EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


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
