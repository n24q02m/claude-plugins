#!/usr/bin/env python3
"""PreToolUse hook: block when better-telegram-mcp credentials are not configured.

Blocking -- Telegram tools cannot function without credentials.
Allows config and help tools through so the user can initiate setup.
"""

import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from mcp_common import check_mcp_credentials, is_mcp_configured

SERVER_NAME = "better-telegram-mcp"
# Either TELEGRAM_PHONE (user mode) or TELEGRAM_BOT_TOKEN (bot mode) is required.
# TELEGRAM_API_ID / TELEGRAM_API_HASH have built-in defaults and are not checked here.
CREDENTIAL_KEYS = ["TELEGRAM_PHONE", "TELEGRAM_BOT_TOKEN"]


def _is_configured() -> bool:
    """Legacy wrapper for backward compatibility with tests."""
    return is_mcp_configured(CREDENTIAL_KEYS)


def main() -> None:
    check_mcp_credentials(
        SERVER_NAME,
        CREDENTIAL_KEYS,
        is_blocking=True,
        block_reason=(
            "better-telegram-mcp credentials not configured. "
            "Set TELEGRAM_PHONE (user mode) or TELEGRAM_BOT_TOKEN (bot mode) "
            "in your MCP server environment, "
            "or use the config tool with action='status' for setup instructions."
        ),
    )


if __name__ == "__main__":
    main()
