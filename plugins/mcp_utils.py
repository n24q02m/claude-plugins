import os
from typing import Iterable

EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def is_configured(keys: Iterable[str]) -> bool:
    """Check if any of the provided environment keys are set or if a config file exists."""
    for k in keys:
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
