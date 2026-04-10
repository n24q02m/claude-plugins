#!/usr/bin/env python3
"""PreToolUse hook: hint when better-email-mcp credentials are not configured.

Non-blocking -- server handles unconfigured state internally via lazy relay
trigger (returns setup instructions with relay URL on first tool call).
"""
import json
import os
import sys

SERVER_NAME = "better-email-mcp"
CREDENTIAL_KEYS = ["EMAIL_CREDENTIALS"]


def _is_configured() -> bool:
    if any(map(os.environ.get, CREDENTIAL_KEYS)):
        return True

    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    # Check common locations without intermediate list creation
    home = os.path.expanduser("~")

    # Linux/macOS default
    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True

    # Windows locations
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data and os.path.exists(os.path.join(local_app_data, "mcp", "config.enc")):
        return True

    app_data = os.environ.get("APPDATA")
    if app_data and os.path.exists(os.path.join(app_data, "mcp", "Config", "config.enc")):
        return True

    return False


def main() -> None:
    if _is_configured():
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
