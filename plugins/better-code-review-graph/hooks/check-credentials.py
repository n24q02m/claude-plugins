#!/usr/bin/env python3
"""PreToolUse hook: hint when better-code-review-graph cloud credentials are not configured.

Non-blocking -- CRG works with local ONNX embedding without cloud credentials.
Only shows a hint so Claude knows cloud embedding is unavailable.
"""
import json
import sys

# Shared utility is injected into the hooks directory during sync
try:
    from mcp_hooks_util import is_configured
except ImportError:
    # Fallback for local development if not in path
    import os
    sys.path.append(os.path.dirname(__file__))
    from mcp_hooks_util import is_configured

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
            "Note: better-code-review-graph cloud credentials not configured. "
            "Using local ONNX embedding -- cloud embedding providers are unavailable. "
            "Use the setup tool with action='start' to configure cloud embedding.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
