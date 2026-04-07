#!/usr/bin/env python3
"""PreToolUse hook: hint when mnemo-mcp cloud credentials are not configured.

Non-blocking -- mnemo-mcp works in FTS5-only mode without cloud credentials.
Only shows a hint so Claude knows semantic search is unavailable.
"""
import json
import os
import sys

SERVER_NAME = "mnemo-mcp"
CLOUD_KEYS = [
    "JINA_AI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
    "CO_API_KEY",
]
# Tools that do not require cloud credentials
EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def _is_configured() -> bool:
    if any(os.environ.get(k) for k in CLOUD_KEYS):
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
        print(
            "Note: mnemo-mcp cloud credentials not configured. "
            "Running in FTS5-only mode -- semantic (vector) search is unavailable. "
            "Use the config tool with action='setup_start' to configure cloud access.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
