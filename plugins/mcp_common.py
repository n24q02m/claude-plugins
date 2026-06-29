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


def check_mcp_credentials(
    server_name: str,
    credential_keys: list[str],
    is_blocking: bool = False,
    custom_message: str | None = None,
) -> None:
    """Centralized credential checking for MCP hooks.

    Checks environment variables and relay configuration.
    Exits with 0 if configured or tool is exempt.
    If unconfigured:
        - If is_blocking=True: prints 'block' decision and exits with 2.
        - If is_blocking=False: prints 'message' hint and exits with 0.
    """
    data = read_mcp_hook_input()
    tool_name = data.get("tool_name", "")
    if not isinstance(tool_name, str):
        tool_name = ""

    exempt_suffixes = ("__setup", "__help", "__config")
    if tool_name.endswith(exempt_suffixes):
        sys.exit(0)

    configured = (
        any(os.environ.get(k) for k in credential_keys) or is_relay_configured()
    )

    if configured:
        sys.exit(0)

    if is_blocking:
        reason = custom_message or f"{server_name} credentials not configured."
        print(json.dumps({"decision": "block", "reason": reason}))
        sys.exit(2)
    else:
        message = (
            custom_message
            or f"{server_name}: credentials not yet configured. The server will provide setup instructions."
        )
        print(json.dumps({"message": message}))
        sys.exit(0)
