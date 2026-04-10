#!/usr/bin/env python3
"""PreToolUse hook: hint when better-notion-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
Notion uses OAuth via claude.ai proxy in HTTP mode.
"""
import json
import os
import sys

# Add plugins directory to sys.path to import shared utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mcp_utils import is_configured

SERVER_NAME = "better-notion-mcp"
CREDENTIAL_KEYS = ["NOTION_TOKEN"]


def main() -> None:
    if is_configured(CREDENTIAL_KEYS):
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
