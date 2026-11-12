#!/usr/bin/env python3
"""PreToolUse hook: hint when better-workspace-mcp credentials are not configured.

Non-blocking -- the server handles the unconfigured state itself (stdio opens
the Google consent screen on first run; HTTP sends each user to /authorize).
Google delegated OAuth means there is no static API token: the env vars below
are the OAuth *client*, not the user's credentials.

A Google account added through the consent flow or `workspace auth` is stored by
hull's PerPluginStore as an encrypted blob in ~/.workspace/config.json (slug
STORE_PLUGIN in src/constants.ts; path layout in hull build/storage/data-dir.js and
backends.js). A store written by an earlier release under ~/.better-workspace/ is
copied forward on startup (src/data-dir-migration.ts), and ~/.better-workspace-mcp/
from even earlier releases is still read as a fallback. The hook checks every one of
those paths, and only checks that the file exists; it never reads or decrypts it.
"""

import json
import os
import sys

# Add plugins root to sys.path for shared utilities
# Add plugins root to sys.path for shared utilities if in marketplace
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
try:
    from mcp_common import read_mcp_hook_input
except ImportError:
    def read_mcp_hook_input() -> dict:
        data = None
        try:
            data = json.loads(sys.stdin.read(64 * 1024))
        except Exception:
            pass
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

SERVER_NAME = "better-workspace-mcp"
CREDENTIAL_KEYS = ["GOOGLE_OAUTH_CLIENT_ID"]
# Per-user account store: current directory first, then the two pre-rename layouts.
STORE_DIRS = (".workspace", ".better-workspace", ".better-workspace-mcp")
EXEMPT_SUFFIXES = ("__setup", "__help", "__config", "__time")


def _is_configured() -> bool:
    for k in CREDENTIAL_KEYS:
        if os.environ.get(k):
            return True
    home = os.path.expanduser("~")
    for p in (home + "/.config/mcp/config.enc", os.path.join(home, ".config", "mcp", "config.enc")):
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

    # Non-blocking hint: let server handle unconfigured state
    print(
        json.dumps(
            {
                "message": (
                    "better-workspace-mcp: credentials not yet configured. "
                    "The server will provide setup instructions."
                ),
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
