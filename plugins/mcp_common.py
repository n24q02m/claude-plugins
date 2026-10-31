import json
import sys


def read_mcp_hook_input() -> dict:
    """Reads and parses a JSON payload from sys.stdin safely (max 64KB).

    Exits with code 2 if the payload is invalid JSON, too large, or not a dict.
    """
    data = None
    try:
        data = json.loads(sys.stdin.read(64 * 1024))
    except Exception:
        pass

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
