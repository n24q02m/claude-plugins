#!/usr/bin/env python3
"""SessionStart hook: peek this agent's agent-chat inbox for unread messages.

Read-only -- never advances any cursor (that happens on `chat.py read`). Prints
one compact summary line when there is something unread, prints nothing when
there isn't, and always exits 0 so a missing/unconfigured chat root never
fails session start. Python stdlib only; works on Windows, WSL and Linux.

Config (env vars, all optional except the first):
  AGENT_CHAT_NAME     this agent's identity in the chat. Unset/empty -> no-op.
  AGENT_CHAT_ROOT     chat root dir. Default: same as chat.py (~/agent-chat).
  AGENT_CHAT_CHANNELS comma-separated channels to check. Empty -> all channels
                      found under the root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _channels_to_check(root: Path, requested: str) -> list[str]:
    wanted = [c.strip() for c in requested.split(",") if c.strip()]
    if wanted:
        return wanted
    return sorted(p.parent.name for p in root.glob("*/_meta.json"))


def main() -> None:
    name = os.environ.get("AGENT_CHAT_NAME", "").strip()
    if not name:
        return

    # Import chat.py from the plugin root (parent of this file's hooks/ dir).
    plugin_root = str(Path(__file__).resolve().parent.parent)
    sys.path.insert(0, plugin_root)
    try:
        import chat
    except Exception:
        return

    try:
        root = chat.root_dir(os.environ.get("AGENT_CHAT_ROOT"))
        if not root.exists():
            return

        unread_by_channel: list[tuple[str, int]] = []
        for ch in _channels_to_check(root, os.environ.get("AGENT_CHAT_CHANNELS", "")):
            chan_dir = chat.channel_dir(root, ch)
            if not (chan_dir / "_meta.json").exists():
                continue
            cursor = chat.read_cursor(chan_dir, name)
            unread = 0
            for p in chat.message_files(chan_dir):
                seq = chat._seq_from_name(p.name)
                if seq is None or seq <= cursor:
                    continue
                if chat.is_relevant(chat.parse_frontmatter(p), name):
                    unread += 1
            if unread:
                unread_by_channel.append((ch, unread))

        if unread_by_channel:
            summary = ", ".join(f"#{ch} ({n})" for ch, n in unread_by_channel)
            print(
                f"[agent-chat] {name} has unread peer messages: {summary}. "
                "Run /agent-chat to read/reply."
            )
    except Exception:
        return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
