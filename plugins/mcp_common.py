import os
import json
import sys


def read_mcp_hook_input() -> dict:
    """Reads and parses a JSON payload from sys.stdin safely (max 32KB).

    Exits with code 2 if the payload is invalid JSON, too large, or not a dict.
    """
    limit = 32 * 1024
    try:
        # Read one extra byte to explicitly detect overflow
        raw_data = sys.stdin.read(limit + 1)
        if len(raw_data) > limit:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": f"Invalid input: payload exceeds {limit // 1024}KB limit",
                    }
                )
            )
            sys.exit(2)

        data = json.loads(raw_data)
        if not isinstance(data, dict):
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": "Invalid input: payload must be a JSON dictionary",
                    }
                )
            )
            sys.exit(2)
        return data
    except Exception:
        # Catch-all to ensure a 'fail-closed' posture as per project guidelines
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": "Invalid input: payload must be a JSON dictionary",
                }
            )
        )
        sys.exit(2)


def is_relay_configured() -> bool:
    """Checks if mcp-relay-core is configured by looking for config.enc."""
    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    # Optimization: Use sequential checks to short-circuit early and
    # avoid constructing unused paths or unnecessary memory allocations.
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and os.path.exists(
        os.path.join(local_app_data, "mcp", "config.enc")
    ):
        return True
    app_data = os.environ.get("APPDATA", "")
    if app_data and os.path.exists(
        os.path.join(app_data, "mcp", "Config", "config.enc")
    ):
        return True
    home = os.path.expanduser("~")
    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True
    return False
