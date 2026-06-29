#!/usr/bin/env python3
"""PreToolUse hook: hint when better-email-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
"""

import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from mcp_common import check_mcp_credentials, is_mcp_configured

SERVER_NAME = "better-email-mcp"
CREDENTIAL_KEYS = ["EMAIL_CREDENTIALS"]


def _is_configured() -> bool:
    """Legacy wrapper for backward compatibility with tests."""
    return is_mcp_configured(CREDENTIAL_KEYS)


def main() -> None:
    check_mcp_credentials(SERVER_NAME, CREDENTIAL_KEYS)


if __name__ == "__main__":
    main()
