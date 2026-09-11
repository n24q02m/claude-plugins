#!/usr/bin/env python3
"""SessionStart hook: peek this agent's agent-chat inbox for unread messages.

Read-only -- never advances any cursor (that happens on `chat.py read` or
`wait`). Prints a compact unread summary, or an identity warning when channels
exist but AGENT_CHAT_NAME is unset. Missing/unconfigured roots stay quiet.
Always exits 0. Python stdlib only; works on Windows, WSL and Linux.

Config (env vars):
  AGENT_CHAT_NAME     this agent's identity; unset -> warn if channels exist.
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


def _bounded_unread_summary(
    entries: list[tuple[str, int]], max_chars: int = 190
) -> str:
    """Render unread channels without exceeding the hook context budget."""
    parts: list[str] = []
    for channel, count in entries:
        item = f"#{channel} ({count})"
        candidate = ", ".join([*parts, item])
        if len(candidate) > max_chars:
            if not parts:
                return item[: max_chars - 1] + "…" if max_chars > 1 else "…"
            return ", ".join([*parts, "…"])
        parts.append(item)
    return ", ".join(parts)


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
            try:
                chan_dir = chat.channel_dir(root, ch)
                if not (chan_dir / "_meta.json").exists():
                    continue
            except (chat.AgentChatError, OSError):
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
                        if chat.is_relevant(
                            chat.parse_frontmatter(Path(entry.path)), name
                        ):
                            unread += 1
            except OSError:
                pass
            if unread:
                unread_by_channel.append((ch, unread))

        if unread_by_channel:
            summary = _bounded_unread_summary(unread_by_channel)
            print(
                f"[agent-chat] {name} has unread peer messages: {summary}. "
                "Run /agent-chat to read/reply."
            )
    # Hook errors must not fail the host session, including SystemExit raised
    # by an imported CLI path.
    except (Exception, SystemExit):
        return


if __name__ == "__main__":
    try:
        main()
    except (Exception, SystemExit):
        pass
    sys.exit(0)
