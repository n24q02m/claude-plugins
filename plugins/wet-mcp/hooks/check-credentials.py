#!/usr/bin/env python3
"""PreToolUse hook: hint when wet-mcp cloud credentials are not configured.

Non-blocking -- wet-mcp works in local mode without cloud credentials.
Only shows a hint so Claude knows cloud features are unavailable.
"""
import json
import os
import sys

SERVER_NAME = "wet-mcp"
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
    for k in CLOUD_KEYS:
        if os.environ.get(k):
            return True
    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    # Optimization: Use sequential checks to short-circuit early and
    # avoid constructing unused paths or unnecessary memory allocations.
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and os.path.exists(os.path.join(local_app_data, "mcp", "config.enc")):
        return True
    app_data = os.environ.get("APPDATA", "")
    if app_data and os.path.exists(os.path.join(app_data, "mcp", "Config", "config.enc")):
        return True
    home = os.path.expanduser("~")
    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True
    return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            sys.exit(0)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name") or ""
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if not _is_configured():
        print(
            "Note: wet-mcp cloud credentials not configured. "
            "Semantic search, cloud embedding, and sync features are unavailable. "
            "Use the setup tool with action='start' to configure cloud access.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
