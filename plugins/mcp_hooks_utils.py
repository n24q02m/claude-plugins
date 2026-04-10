import os

def is_configured(keys) -> bool:
    """Check if any of the provided environment keys are set or if mcp-relay-core config exists."""
    if any(os.environ.get(k) for k in keys):
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

    return any(os.path.exists(p) for p in paths)
