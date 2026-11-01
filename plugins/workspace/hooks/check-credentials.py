#!/usr/bin/env python3
"""PreToolUse hook: hint when better-workspace-mcp credentials are not configured.

Non-blocking hint only. Google delegated OAuth means there is no static API
token: the env vars below are your own OAuth *client*, not the user's
credentials. In stdio mode the first run opens the Google consent screen; in
HTTP mode each user consents with `workspace auth --user <namespace>` on the
host. There is no browser setup form served over HTTP.

A Google account added through the consent flow or `workspace auth` is stored
as an encrypted blob in ~/.better-workspace/config.json. Earlier releases wrote
to ~/.better-workspace-mcp/, which the server still reads as a fallback. The
hook only checks that the file exists; it never reads or decrypts it.
"""

import json
import os
import sys

# Add plugins root to sys.path for shared utilities
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from mcp_common import read_mcp_hook_input

SERVER_NAME = "better-workspace-mcp"
CREDENTIAL_KEYS = ["GOOGLE_OAUTH_CLIENT_ID"]
# Per-user account store: current directory first, then the pre-rename directory.
STORE_DIRS = (".better-workspace", ".better-workspace-mcp")
EXEMPT_SUFFIXES = ("__setup", "__help", "__config", "__time")


def _is_configured() -> bool:
    for k in CREDENTIAL_KEYS:
        if os.environ.get(k):
            return True
    home = os.path.expanduser("~")
    for p in (
        home + "/.config/mcp/config.enc",
        os.path.join(home, ".config", "mcp", "config.enc"),
    ):
        if os.path.exists(p):
            return True
    for store_dir in STORE_DIRS:
        if os.path.exists(os.path.join(home, store_dir, "config.json")):
            return True
    return False


def main() -> None:
    data = read_mcp_hook_input()

    tool_name = data.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    if tool_name.endswith(EXEMPT_SUFFIXES):
        sys.exit(0)

    if _is_configured():
        sys.exit(0)

    # Non-blocking hint: point at the real setup path (own OAuth client, then
    # the consent screen on first run)
    print(
        json.dumps(
            {
                "message": (
                    "better-workspace-mcp: credentials not yet configured. "
                    "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET "
                    "(your own Google OAuth client) in the plugin config; the "
                    "first run then opens the Google consent screen."
                ),
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
