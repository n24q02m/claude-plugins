import os
from typing import Iterable

CLOUD_KEYS = (
    "JINA_AI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
    "CO_API_KEY",
)

EXEMPT_SUFFIXES = ("__setup", "__help", "__config")


def is_configured(keys: Iterable[str]) -> bool:
    """Check if any of the provided environment variables are set or if a local config exists."""
    for k in keys:
        if os.environ.get(k):
            return True

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    home = os.path.expanduser("~")

    # mcp-relay-core stores config.enc in a shared 'mcp' directory
    paths = [
        p
        for p in [
            os.path.join(local_app_data, "mcp", "config.enc") if local_app_data else "",
            os.path.join(app_data, "mcp", "Config", "config.enc") if app_data else "",
            os.path.join(home, ".config", "mcp", "config.enc"),
        ]
        if p
    ]

    for p in paths:
        if os.path.exists(p):
            return True
    return False
