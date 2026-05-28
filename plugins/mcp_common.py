import json
import os
import sys
from typing import Any, Dict


def read_mcp_hook_input() -> Dict[str, Any]:
    """Reads and validates MCP hook input from stdin."""
    try:
        # Use bounded read to prevent memory exhaustion DoS
        data = json.loads(sys.stdin.read(1024 * 1024))
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Fail consistently for invalid input
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
