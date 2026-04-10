#!/usr/bin/env python3
"""PreToolUse hook: hint when better-code-review-graph cloud credentials are not configured.

Non-blocking -- CRG works with local ONNX embedding without cloud credentials.
Only shows a hint so Claude knows cloud embedding is unavailable.
"""
import json
import os
import sys
from pathlib import Path

# Add plugins directory to sys.path to allow importing mcp_common
sys.path.append(str(Path(__file__).parent.parent.parent))
from mcp_common import CLOUD_KEYS, EXEMPT_SUFFIXES, is_configured

SERVER_NAME = "better-code-review-graph"


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
