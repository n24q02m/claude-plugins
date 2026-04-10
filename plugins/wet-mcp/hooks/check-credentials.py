#!/usr/bin/env python3
"""PreToolUse hook: hint when wet-mcp cloud credentials are not configured.

Non-blocking -- wet-mcp works in local mode without cloud credentials.
Only shows a hint so Claude knows cloud features are unavailable.
"""
import json
import os
import sys
from pathlib import Path

# Add plugins directory to sys.path to allow importing mcp_common
sys.path.append(str(Path(__file__).parent.parent.parent))
from mcp_common import CLOUD_KEYS, EXEMPT_SUFFIXES, is_configured

SERVER_NAME = "wet-mcp"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if not is_configured(CLOUD_KEYS):
        print(
            "Note: wet-mcp cloud credentials not configured. "
            "Semantic search, cloud embedding, and sync features are unavailable. "
            "Use the setup tool with action='start' to configure cloud access.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
