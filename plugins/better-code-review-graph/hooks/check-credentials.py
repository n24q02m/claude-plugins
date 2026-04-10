#!/usr/bin/env python3
"""PreToolUse hook: hint when better-code-review-graph cloud credentials are not configured.

Non-blocking -- CRG works with local ONNX embedding without cloud credentials.
Only shows a hint so Claude knows cloud embedding is unavailable.
"""
import json
import os
import sys

SERVER_NAME = "better-code-review-graph"
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
    home = os.path.expanduser("~")
    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    # Check common paths directly to avoid list allocations and joins
    path = os.environ.get("LOCALAPPDATA")
    if path and os.path.exists(os.path.join(path, "mcp", "config.enc")):
        return True

    path = os.environ.get("APPDATA")
    if path and os.path.exists(os.path.join(path, "mcp", "Config", "config.enc")):
        return True

    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
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
            "Note: better-code-review-graph cloud credentials not configured. "
            "Using local ONNX embedding -- cloud embedding providers are unavailable. "
            "Use the setup tool with action='start' to configure cloud embedding.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
