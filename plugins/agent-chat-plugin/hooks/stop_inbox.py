#!/usr/bin/env python3
"""Stop hook: warn when this agent is ending a turn with unread peer messages."""

from __future__ import annotations

import json
import os
import sys
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


def main() -> None:
    name = os.environ.get("AGENT_CHAT_NAME", "").strip()
    if not name:
        return

    plugin_root = str(Path(__file__).resolve().parent.parent)
    sys.path.insert(0, plugin_root)
    try:
        import chat
        from session_inbox import _channels_to_check
    except Exception:
        return

    try:
        root = chat.root_dir(os.environ.get("AGENT_CHAT_ROOT"))
        if not root.exists():
            return

        unread_by_channel: list[tuple[str, int]] = []
        for channel in _channels_to_check(
            root, os.environ.get("AGENT_CHAT_CHANNELS", "")
        ):
            try:
                with redirect_stderr(StringIO()):
                    channel_path = chat.channel_dir(root, channel)
            except SystemExit:
                continue
            if not (channel_path / "_meta.json").exists():
                continue

            cursor = chat.read_cursor(channel_path, name)
            unread = 0
            for message in chat.message_files(channel_path):
                sequence = chat._seq_from_name(message.name)
                if sequence is None or sequence <= cursor:
                    continue
                if chat.is_relevant(chat.parse_frontmatter(message), name):
                    unread += 1
            if unread:
                unread_by_channel.append((channel, unread))

        if unread_by_channel:
            summary = ", ".join(
                f"#{channel} ({count})" for channel, count in unread_by_channel
            )
            print(
                json.dumps(
                    {
                        "systemMessage": (
                            "[agent-chat] Your turn is ending with unread peer messages: "
                            f"{summary}. Run /agent-chat to read/reply."
                        )
                    }
                )
            )
    except (Exception, SystemExit):
        return


if __name__ == "__main__":
    try:
        main()
    except (Exception, SystemExit):
        pass
    sys.exit(0)
