import sys

def update_file(filepath, keys_var):
    with open(filepath, 'r') as f:
        content = f.read()

    # Matching the block I just created
    old_block = f"""def _is_configured() -> bool:
    if any(os.environ.get(k) for k in {keys_var}):
        return True

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data and os.path.exists(os.path.join(local_app_data, "mcp", "config.enc")):
        return True

    app_data = os.environ.get("APPDATA")
    if app_data and os.path.exists(os.path.join(app_data, "mcp", "Config", "config.enc")):
        return True

    home = os.path.expanduser("~")
    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True

    return False"""

    new_block = f"""def _is_configured() -> bool:
    for k in {keys_var}:
        if os.environ.get(k):
            return True

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        if os.path.exists(os.path.join(local_app_data, "mcp", "config.enc")):
            return True

    app_data = os.environ.get("APPDATA")
    if app_data:
        if os.path.exists(os.path.join(app_data, "mcp", "Config", "config.enc")):
            return True

    home = os.path.expanduser("~")
    if os.path.exists(os.path.join(home, ".config", "mcp", "config.enc")):
        return True

    return False"""

    if old_block in content:
        new_content = content.replace(old_block, new_block)
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Refined {filepath}")
    else:
        print(f"Could not find target block in {filepath}")

update_file("plugins/better-code-review-graph/hooks/check-credentials.py", "CLOUD_KEYS")
update_file("plugins/mnemo-mcp/hooks/check-credentials.py", "CLOUD_KEYS")
update_file("plugins/wet-mcp/hooks/check-credentials.py", "CLOUD_KEYS")
update_file("plugins/better-telegram-mcp/hooks/check-credentials.py", "CREDENTIAL_KEYS")
update_file("plugins/better-notion-mcp/hooks/check-credentials.py", "CREDENTIAL_KEYS")
update_file("plugins/better-email-mcp/hooks/check-credentials.py", "CREDENTIAL_KEYS")
