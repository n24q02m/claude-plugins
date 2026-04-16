import os
from typing import Iterable

def is_configured(credential_keys: Iterable[str]) -> bool:
    """Checks if the plugin is configured via environment variables or config file.

    This utility checks:
    1. Any of the provided environment variable keys are set.
    2. The standard mcp-relay-core config.enc file exists in common locations.
    """
    for k in credential_keys:
        if os.environ.get(k):
            return True

    # Check for config.enc in standard locations with early returns to avoid allocations
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        p = os.path.join(local_app_data, "mcp", "config.enc")
        if os.path.exists(p):
            return True

    app_data = os.environ.get("APPDATA")
    if app_data:
        p = os.path.join(app_data, "mcp", "Config", "config.enc")
        if os.path.exists(p):
            return True

    home = os.path.expanduser("~")
    p = os.path.join(home, ".config", "mcp", "config.enc")
    if os.path.exists(p):
        return True

    return False
