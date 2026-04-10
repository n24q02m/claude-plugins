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
    env = os.environ
    for k in CLOUD_KEYS:
        if env.get(k):
            return True

    # Check for mcp-relay-core config.enc in shared directories
    local_app_data = env.get("LOCALAPPDATA")
    if local_app_data and os.path.exists(os.path.join(local_app_data, "mcp", "config.enc")):
        return True

    app_data = env.get("APPDATA")
    if app_data and os.path.exists(os.path.join(app_data, "mcp", "Config", "config.enc")):
        return True

    home = os.path.expanduser("~")
    if home and os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True

    return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
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
