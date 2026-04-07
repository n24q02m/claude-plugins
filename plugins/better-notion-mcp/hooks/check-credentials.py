#!/usr/bin/env python3
"""PreToolUse hook: block when better-notion-mcp credentials are not configured.

Blocking -- Notion tools cannot function without a NOTION_TOKEN.
Allows help tool through so the user can read documentation.
"""
import json
import os
import sys

SERVER_NAME = "better-notion-mcp"
CREDENTIAL_KEYS = ["NOTION_TOKEN"]
# Tools that work without credentials
EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def _is_configured() -> bool:
    if any(os.environ.get(k) for k in CREDENTIAL_KEYS):
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
    return any(os.path.exists(p) for p in paths)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if any(tool_name.endswith(s) for s in EXEMPT_SUFFIXES):
        sys.exit(0)

    if not _is_configured():
        print(json.dumps({
            "decision": "block",
            "reason": (
                "better-notion-mcp credentials not configured. "
                "Set NOTION_TOKEN in your MCP server environment "
                "(get a token from https://www.notion.so/my-integrations), "
                "or restart Claude Code to trigger the relay setup flow."
            ),
        }))
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
