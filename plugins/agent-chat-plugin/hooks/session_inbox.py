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
  CLAUDE_PLUGIN_ROOT  plugin root (set by Claude Code). Unset/empty -> this
                      script's own directory chain; unresolvable -> skip.

"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _channels_to_check(root: Path, requested: str) -> list[str]:
    wanted = [c.strip() for c in requested.split(",") if c.strip()]
    if wanted:
        return wanted
    found = []
    # Optimization: Use os.scandir instead of Path.glob("*/_meta.json") to discover channels.
    # This avoids instantiating thousands of Path objects for discarded subdirectories.
    # Filters out hidden directories (starting with '.') to maintain parity with glob("*").
    try:
        with os.scandir(root) as it:
            for entry in it:
                if (
                    not entry.name.startswith(".")
                    and entry.is_dir()
                    and os.path.exists(os.path.join(entry.path, "_meta.json"))
                ):
                    found.append(entry.name)
    except OSError:
        pass
    return sorted(found)


def main() -> None:
    # Import chat.py from the plugin root. Claude Code sets CLAUDE_PLUGIN_ROOT
    # for hook commands; other harnesses fall back to this script's own
    # directory chain (hooks/ lives directly under the plugin root).
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
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
    except Exception:
        return

    try:
        root = chat.root_dir(os.environ.get("AGENT_CHAT_ROOT"))
        if not root.exists():
            return

        name = os.environ.get("AGENT_CHAT_NAME", "").strip()
        if not name:
            has_channels = False
            # Optimization: Use os.scandir instead of any(Path.glob("*/_meta.json")) for early exit.
            # This avoids instantiating thousands of Path objects for discarded subdirectories.
            # Filters out hidden directories (starting with '.') to maintain parity with glob("*").
            try:
                with os.scandir(root) as it:
                    for entry in it:
                        if (
                            not entry.name.startswith(".")
                            and entry.is_dir()
                            and os.path.exists(os.path.join(entry.path, "_meta.json"))
                        ):
                            has_channels = True
                            break
            except OSError:
                pass
            if has_channels:
                print(
                    "[agent-chat] Inbox hook disabled: identity is unset; "
                    "set AGENT_CHAT_NAME."
                )
            return

        unread_by_channel: list[tuple[str, int]] = []
        for ch in _channels_to_check(root, os.environ.get("AGENT_CHAT_CHANNELS", "")):
            chan_dir = chat.channel_dir(root, ch)
            if not (chan_dir / "_meta.json").exists():
                continue
            cursor = chat.read_cursor(chan_dir, name)
            unread = 0
            # Optimization: use os.scandir to avoid Path instantiation overhead for
            # thousands of old messages per tick.
            try:
                with os.scandir(chan_dir) as it:
                    for entry in it:
                        if not entry.name.endswith(".md"):
                            continue
                        seq = chat._seq_from_name(entry.name)
                        if seq is None or seq <= cursor:
                            continue
                        if chat.is_relevant(chat.parse_frontmatter(Path(entry.path)), name):
                            unread += 1
            except OSError:
                pass
            if unread:
                unread_by_channel.append((ch, unread))

        if unread_by_channel:
            summary = ", ".join(f"#{ch} ({n})" for ch, n in unread_by_channel)
            print(
                f"[agent-chat] {name} has unread peer messages: {summary}. "
                "Run /agent-chat to read/reply."
            )
    # SystemExit too: chat.channel_dir() calls die() on a malformed channel name
    # (e.g. a stray entry in AGENT_CHAT_CHANNELS), and SystemExit is a
    # BaseException -- an `except Exception` alone would let it fail the session.
    except (Exception, SystemExit):
        return


if __name__ == "__main__":
    try:
        main()
    except (Exception, SystemExit):
        pass
    sys.exit(0)
