#!/usr/bin/env python3
"""UserPromptSubmit hook: non-blockingly notify about unread peer messages."""

from __future__ import annotations

import os
import sys
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


def main() -> None:
    name = os.environ.get("AGENT_CHAT_NAME", "").strip()
    if not name:
        return

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
        # Fallback for harnesses that don't set CLAUDE_PLUGIN_ROOT: this
        # script's own directory chain (hooks/ lives under the plugin root).
        plugin_root = str(Path(__file__).resolve().parent.parent)
    if not (Path(plugin_root) / "chat.py").is_file():
        # Skip-not-crash: a hook must never fail a harness session.
        print(
            "[agent-chat] skipping inbox check: plugin root unresolved "
            f"(no chat.py under {plugin_root}); hook is non-blocking",
            file=sys.stderr,
        )
        return
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
            try:
                with os.scandir(channel_path) as it:
                    for entry in it:
                        if not entry.name.endswith(".md"):
                            continue
                        sequence = chat._seq_from_name(entry.name)
                        if sequence is None or sequence <= cursor:
                            continue
                        if chat.is_relevant(chat.parse_frontmatter(Path(entry.path)), name):
                            unread += 1
            except OSError:
                pass
            if unread:
                unread_by_channel.append((channel, unread))

        if unread_by_channel:
            summary = ", ".join(
                f"#{channel} ({count})" for channel, count in unread_by_channel
            )
            print(
                f"[agent-chat] {name} has unread peer messages: {summary}. "
                "Run /agent-chat to read/reply."
            )
    except (Exception, SystemExit):
        return


if __name__ == "__main__":
    try:
        main()
    except (Exception, SystemExit):
        pass
    sys.exit(0)
