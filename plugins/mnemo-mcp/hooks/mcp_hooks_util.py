import os
from typing import Iterable

def is_configured(credential_keys: Iterable[str]) -> bool:
    """
    Check if the MCP server is configured either via environment variables
    or via a shared config file.
    """
    for k in credential_keys:
        if os.environ.get(k):
            return True

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    home = os.path.expanduser("~")

    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    paths = [p for p in [
        os.path.join(local_app_data, "mcp", "config.enc") if local_app_data else "",
        os.path.join(app_data, "mcp", "Config", "config.enc") if app_data else "",
        os.path.join(home, ".config", "mcp", "config.enc"),
    ] if p]

    for p in paths:
        if os.path.exists(p):
            return True

    return False
