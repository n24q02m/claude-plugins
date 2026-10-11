#!/usr/bin/env python3
"""PreToolUse hook: hint when better-workspace-mcp credentials are not configured.

Non-blocking -- the server handles the unconfigured state itself (stdio opens
the Google consent screen on first run; HTTP sends each user to /authorize).
Google delegated OAuth means there is no static API token: the env vars below
are the OAuth *client*, not the user's credentials.
"""

import json
import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from mcp_common import is_relay_configured, read_mcp_hook_input

SERVER_NAME = "better-workspace-mcp"
CREDENTIAL_KEYS = ["GOOGLE_OAUTH_CLIENT_ID"]
EXEMPT_SUFFIXES = ("__setup", "__help", "__config", "__time")


def _is_configured() -> bool:
    for k in CREDENTIAL_KEYS:
        if os.environ.get(k):
            return True
    return is_relay_configured()


def main() -> None:
    data = read_mcp_hook_input()

    tool_name = data.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if _is_configured():
        sys.exit(0)

    # Non-blocking hint: let server handle unconfigured state
    print(
        json.dumps(
            {
                "message": (
                    "better-workspace-mcp: credentials not yet configured. "
                    "The server will provide setup instructions."
                ),
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
