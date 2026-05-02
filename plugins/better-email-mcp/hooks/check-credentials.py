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
    for k in CREDENTIAL_KEYS:
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
            print(json.dumps({
                "decision": "block",
                "reason": "Invalid input: payload must be a JSON dictionary",
            }))
            sys.exit(2)
    except Exception:
        print(json.dumps({
            "decision": "block",
            "reason": "Invalid input: payload must be a JSON dictionary",
        }))
        sys.exit(2)

    tool_name = data.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    if tool_name.endswith(("__setup", "__help", "__config")):
        sys.exit(0)

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
