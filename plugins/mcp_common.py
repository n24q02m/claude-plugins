import os
import json
import sys


def read_mcp_hook_input() -> dict:
    """Reads and parses a JSON payload from sys.stdin safely (max 64KB).

    Exits with code 2 if the payload is invalid JSON, too large, or not a dict.
    """
    try:
        data = json.loads(sys.stdin.read(64 * 1024))
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
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": "Invalid input: payload must be a JSON dictionary",
                }
            )
        )
        sys.exit(2)


def check_mcp_credentials(
    server_name: str,
    credential_keys: list[str],
    exempt_suffixes: tuple[str, ...] = ("__setup", "__help", "__config"),
    is_blocking: bool = False,
    custom_message: str | None = None,
) -> None:
    """Shared logic for checking credentials in MCP PreToolUse hooks.

    Exits with code 0 if configured or tool is exempt.
    Exits with code 2 if blocking and not configured.
    Prints a message and exits with code 0 if non-blocking and not configured.
    """
    data = read_mcp_hook_input()
    tool_name = data.get("tool_name", "")
    if not isinstance(tool_name, str):
        tool_name = ""

    if tool_name.endswith(exempt_suffixes):
        sys.exit(0)

    is_configured = (
        any(os.environ.get(k) for k in credential_keys) or is_relay_configured()
    )

    if is_configured:
        sys.exit(0)

    if is_blocking:
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": custom_message
                    or f"{server_name} credentials not configured.",
                }
            )
        )
        sys.exit(2)
    else:
        print(
            json.dumps(
                {
                    "message": custom_message
                    or f"{server_name}: credentials not yet configured.",
                }
            )
        )
        sys.exit(0)


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
