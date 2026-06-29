#!/usr/bin/env python3
"""PreToolUse hook: hint when better-email-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
"""

import json
import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from mcp_common import check_mcp_credentials, read_mcp_hook_input

SERVER_NAME = "better-email-mcp"
CREDENTIAL_KEYS = ["EMAIL_CREDENTIALS"]
EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def main() -> None:
    data = read_mcp_hook_input()

    tool_name = data.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if check_mcp_credentials(CREDENTIAL_KEYS):
        sys.exit(0)

    # Non-blocking hint: let server handle unconfigured state
    # Server's lazy trigger will open relay and return setup instructions
    print(
        json.dumps(
            {
                "message": (
                    "better-email-mcp: credentials not yet configured. "
                    "The server will provide setup instructions."
                ),
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
