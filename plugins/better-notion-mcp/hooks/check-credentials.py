#!/usr/bin/env python3
"""PreToolUse hook: hint when better-notion-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
Notion uses OAuth via claude.ai proxy in HTTP mode.
"""

import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from mcp_common import check_mcp_credentials

SERVER_NAME = "better-notion-mcp"
CREDENTIAL_KEYS = ["NOTION_TOKEN"]


def main() -> None:
    check_mcp_credentials(
        server_name=SERVER_NAME,
        credential_keys=CREDENTIAL_KEYS,
        is_blocking=False,
    )


if __name__ == "__main__":
    main()
