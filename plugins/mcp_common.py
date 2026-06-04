import functools
import os


# Optimization: Cache the result to avoid repeated filesystem I/O for a configuration that rarely changes during execution. Expected impact: O(1) subsequent calls.
@functools.lru_cache(maxsize=1)
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
