#!/usr/bin/env python3
"""PreToolUse hook: hint when better-email-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
"""
import json
import os
import sys

# Add the plugins directory to sys.path to import shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mcp_config_utils import is_configured

SERVER_NAME = "better-email-mcp"
CREDENTIAL_KEYS = ["EMAIL_CREDENTIALS"]


def main() -> None:
    if is_configured(CREDENTIAL_KEYS):
        sys.exit(0)

    # Non-blocking hint: let server handle unconfigured state
    # Server's lazy trigger will open relay and return setup instructions
    print(json.dumps({
        "message": (
            "better-email-mcp: credentials not yet configured. "
            "The server will provide setup instructions."
        ),
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
