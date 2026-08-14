#!/usr/bin/env python3
"""agent-chat: peer-to-peer coordination for multiple agent sessions via markdown files.

Zero-dependency (Python stdlib only) so it runs identically on Windows, WSL and
Linux -- the same `python3` every session on the home + company machines already
has. No inotify/fswatch split: `wait` blocks with a sleep-poll loop, so while an
agent waits for a reply the Python process is idle and burns ZERO model tokens.

Model
-----
A ROOT dir holds CHANNELS (one folder each = one "group chat"). Each channel holds
numbered message files `NNNN-<from>-<slug>.md` with YAML frontmatter, a `_meta.json`
(members/topic) and per-agent read cursors under `.cursors/`. Sequence numbers are
allocated under a filesystem lock (atomic `mkdir`) so two sessions can never claim
the same number -- the exact race that produced duplicate "seq 11" files in the
hand-rolled prototype.

Commands: init | channels | roster | post | read | wait | peek | claim
Run `python chat.py <command> --help` for flags.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path

import heapq

# --- root + small helpers ----------------------------------------------------


def root_dir(explicit: str | None) -> Path:
    # Precedence: --root flag > AGENT_CHAT_ROOT env > ~/agent-chat default.
    base = (
        explicit or os.environ.get("AGENT_CHAT_ROOT") or str(Path.home() / "agent-chat")
    )
    return Path(base)


def now_iso() -> str:
    # Local time WITH offset so a git-committed thread is unambiguous across machines.
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-")) or "msg"


def _frontmatter_value(value) -> str:
    """Keep a dynamic frontmatter value on exactly one physical line."""
    return re.sub(r"[\r\n]+", " ", str(value))


class AgentChatError(Exception):
    pass


def die(msg: str, code: int = 1):
    print(f"agent-chat: {msg}", file=sys.stderr)
    raise SystemExit(code)


# --- channel + message primitives -------------------------------------------


def _check_safe_name(name: str, kind: str):
    """Prevent path traversal vulnerabilities."""
    if not name or "/" in name or "\\" in name or ":" in name or name in (".", ".."):
        raise AgentChatError(f"invalid {kind} name (path traversal blocked): '{name}'")
    if name.startswith(".") or name.startswith("_"):
        raise AgentChatError(f"invalid {kind} name (reserved prefix blocked): '{name}'")


_TASK_MARKER_RE = re.compile(r"task-[A-Za-z0-9][A-Za-z0-9_-]*\.md")


def channel_dir(root: Path, channel: str) -> Path:
    _check_safe_name(channel, "channel")
    return root / channel


def require_channel(root: Path, channel: str) -> Path:
    d = channel_dir(root, channel)
    if not (d / "_meta.json").exists():
        raise AgentChatError(
            f"channel '{channel}' not found under {root} (run: init {channel})"
        )
    return d


def _seq_from_name(name: str) -> int | None:
    m = re.match(r"(\d+)-", name)
    return int(m.group(1)) if m else None


def message_files(chan: Path):
    files = [p for p in chan.glob("*.md") if _seq_from_name(p.name) is not None]
    return sorted(files, key=lambda p: _seq_from_name(p.name))


def parse_frontmatter(path: Path) -> dict:
    """Minimal front-matter reader: the block between the first two '---' lines.

    Values are strings except `to`, normalized to a list ([] == broadcast/all).
    """
    meta: dict = {}
    try:
        with path.open(encoding="utf-8") as f:
            first_line = f.readline()
            if not first_line.startswith("---"):
                return meta
            temp_meta = {}
            found_end = False
            for line in f:
                stripped = line.strip()
                if stripped == "---":
                    found_end = True
                    break
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                temp_meta[k.strip()] = v.strip()
            if not found_end:
                return meta
            meta = temp_meta
    except (OSError, UnicodeDecodeError):
        return meta
    # Normalize `to` -> list of recipients (empty == everyone).
    raw = meta.get("to", "").strip()
    if raw in ("", "all", "[]", "*"):
        meta["to_list"] = []
    else:
        meta["to_list"] = [x.strip() for x in raw.strip("[]").split(",") if x.strip()]
    return meta


def is_relevant(meta: dict, agent: str) -> bool:
    # A message concerns `agent` if it's a broadcast or explicitly addressed to
    # them, and it isn't their own message (don't wake an agent on its own post).
    if meta.get("from") == agent:
        return False
    to = meta.get("to_list", [])
    return (not to) or (agent in to)


# --- atomic sequence lock ----------------------------------------------------


def _acquire_lock(chan: Path, timeout: float = 10.0, stale: float = 30.0) -> Path:
    """Atomic cross-platform lock via mkdir (fails if the dir already exists).

    Steals a lock older than `stale` seconds so a crashed poster can't wedge the
    channel forever.
    """
    lock = chan / "_seq.lock"
    start = time.time()
    while True:
        try:
            os.mkdir(lock)
            return lock
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    try:
                        os.rmdir(lock)
                    except OSError:
                        pass
                    continue
            except FileNotFoundError:
                continue
            if time.time() - start > timeout:
                raise AgentChatError(
                    "could not acquire channel seq lock (another poster is stuck?)"
                )
            time.sleep(0.05)


def _release_lock(lock: Path):
    try:
        os.rmdir(lock)
    except OSError:
        pass


def _next_seq(chan: Path) -> int:
    mx = 0
    for p in chan.glob("*.md"):
        s = _seq_from_name(p.name)
        if s is not None:
            mx = max(mx, s)
    return mx + 1


# --- cursors -----------------------------------------------------------------


def cursor_path(chan: Path, agent: str) -> Path:
    return chan / ".cursors" / f"{slugify(agent)}.txt"


def read_cursor(chan: Path, agent: str) -> int:
    p = cursor_path(chan, agent)
    try:
        return int(p.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def write_cursor(chan: Path, agent: str, seq: int):
    p = cursor_path(chan, agent)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(seq), encoding="utf-8")


def max_seq(chan: Path) -> int:
    maximum = 0
    for path in chan.glob("*.md"):
        seq = _seq_from_name(path.name)
        if seq is not None and seq > maximum:
            maximum = seq
    return maximum


# --- commands ----------------------------------------------------------------


def cmd_init(root: Path, a):
    d = channel_dir(root, a.channel)
    d.mkdir(parents=True, exist_ok=True)
    (d / ".cursors").mkdir(exist_ok=True)
    meta_path = d / "_meta.json"
    if meta_path.exists():
        raise AgentChatError(f"channel '{a.channel}' already exists")
    members = [m.strip() for m in (a.members or "").split(",") if m.strip()]
    meta_path.write_text(
        json.dumps(
            {
                "channel": a.channel,
                "members": members,
                "topic": a.topic or "",
                "created": now_iso(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    m_str = ", ".join(members) if members else "(open)"
    print(f"created channel '{a.channel}' at {d}  members={m_str}")


def cmd_channels(root: Path, a):
    if not root.exists():
        print(f"(no channels yet under {root})")
        return
    rows = []
    for meta_path in sorted(root.glob("*/_meta.json")):
        chan = meta_path.parent
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        count = 0
        last_path = None
        last_seq = 0
        for path in chan.glob("*.md"):
            seq = _seq_from_name(path.name)
            if seq is None:
                continue
            count += 1
            if last_path is None or seq > last_seq:
                last_path = path
                last_seq = seq
        last = "-"
        if last_path is not None:
            lm = parse_frontmatter(last_path)
            title = lm.get("title", "")
            if len(title) > 40:
                title = title[:37] + "..."
            last = f"#{last_seq} {lm.get('from', '?')}: {title}"
        members_str = ", ".join(meta.get("members", [])) or "(open)"
        if len(members_str) > 40:
            members_str = members_str[:37] + "..."
        rows.append(
            (chan.name, members_str, count, last)
        )
    if not rows:
        print(f"(no channels yet under {root})")
        return
    w = max(len("CHANNEL"), max(len(r[0]) for r in rows))
    print(f"{'CHANNEL'.ljust(w)}  MSGS  MEMBERS / LAST")
    for name, members, n, last in rows:
        print(f"{name.ljust(w)}  {str(n).rjust(4)}  {members}")
        print(f"{' '.ljust(w)}        last: {last}")


def cmd_roster(root: Path, a):
    d = require_channel(root, a.channel)
    try:
        meta = json.loads((d / "_meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise AgentChatError(f"could not read or parse _meta.json for channel '{a.channel}'")
    print(f"channel : {meta.get('channel')}")
    print(f"topic   : {meta.get('topic') or '(none)'}")
    print(f"members : {', '.join(meta.get('members', [])) or '(open)'}")
    count = sum(1 for p in d.glob("*.md") if _seq_from_name(p.name) is not None)
    print(f"messages: {count}")


def _read_body(a) -> str:
    if a.body is not None:
        return a.body
    if a.body_file:
        try:
            return Path(a.body_file).read_text(encoding="utf-8")
        except OSError as e:
            raise AgentChatError(f"could not read body file: {e}")
    # Default: read from stdin so agents can pipe long markdown bodies.
    if sys.stdin.isatty():
        print(
            "agent-chat: Enter message body; press Ctrl-D (or Ctrl-Z and Enter on Windows) to finish.",
            file=sys.stderr,
        )
    data = sys.stdin.read()
    if not data.strip():
        raise AgentChatError("empty body (pass --body, --body-file, or pipe via stdin)")
    return data


def cmd_post(root: Path, a):
    d = require_channel(root, a.channel)
    body = _read_body(a)
    sender = _frontmatter_value(a.sender)
    to = _frontmatter_value(a.to or "all")
    reply = _frontmatter_value(a.reply) if a.reply else None
    channel = _frontmatter_value(a.channel)
    timestamp = _frontmatter_value(now_iso())
    status = _frontmatter_value(a.status)
    title = _frontmatter_value(a.title)
    lock = _acquire_lock(d)
    try:
        seq = _next_seq(d)
        fname = f"{seq:04d}-{slugify(a.sender)}-{slugify(a.title)}.md"
        fm = [
            "---",
            f"seq: {seq}",
            f"from: {sender}",
            f"to: {to}",
        ]
        if reply is not None:
            fm.append(f"reply_to: {reply}")
        fm += [
            f"channel: {channel}",
            f"ts: {timestamp}",
            f"status: {status}",
            f"title: {title}",
            "---",
            "",
        ]
        (d / fname).write_text("\n".join(fm) + body.rstrip() + "\n", encoding="utf-8")
    finally:
        _release_lock(lock)
    print(f"posted #{seq} -> {a.channel}/{fname}")


def _print_message(path: Path):
    print("=" * 70)
    print(path.read_text(encoding="utf-8").rstrip())
    print()


def cmd_read(root: Path, a):
    d = require_channel(root, a.channel)
    cur = 0 if a.all else read_cursor(d, a.agent)
    shown = 0

    # Optimization: One O(N) glob scan to find both top seq and unread messages,
    # avoiding O(N log N) message_files sort and redundant max_seq glob.
    found = []
    top = 0
    for p in d.glob("*.md"):
        seq = _seq_from_name(p.name)
        if seq is None:
            continue
        if seq > top:
            top = seq
        if seq > cur:
            found.append((seq, p))

    found.sort(key=lambda x: x[0])

    for seq, p in found:
        meta = parse_frontmatter(p)
        if not a.all and not is_relevant(meta, a.agent):
            continue
        _print_message(p)
        shown += 1

    if not a.peek:
        write_cursor(d, a.agent, top)
    if shown == 0:
        print(f"(no new messages for {a.agent} in '{a.channel}'; cursor at #{cur})")


def cmd_wait(root: Path, a):
    d = require_channel(root, a.channel)
    cur = read_cursor(d, a.agent)
    deadline = time.time() + a.timeout
    while True:
        found = []
        # Optimization: use os.scandir to avoid Path instantiation overhead for
        # thousands of old messages per tick.
        try:
            with os.scandir(d) as it:
                for entry in it:
                    if not entry.name.endswith(".md"):
                        continue
                    seq = _seq_from_name(entry.name)
                    if seq is None or seq <= cur:
                        continue
                    p = Path(entry.path)
                    meta = parse_frontmatter(p)
                    if is_relevant(meta, a.agent):
                        found.append(p)
        except OSError:
            pass
        if found:
            # Sort only the newly found messages
            found.sort(key=lambda p: _seq_from_name(p.name))
            for p in found:
                _print_message(p)
            write_cursor(d, a.agent, max_seq(d))
            return
        if time.time() >= deadline:
            print(
                f"(timeout after {a.timeout}s: no new messages for {a.agent} in '{a.channel}')",
                file=sys.stderr,
            )
            raise SystemExit(2)
        time.sleep(a.interval)


def cmd_peek(root: Path, a):
    d = require_channel(root, a.channel)

    if a.n <= 0:
        return

    # Optimization: Use a min-heap to find top N messages in O(N log K) time
    # rather than sorting all messages O(N log N) via message_files()
    top_n = []
    for p in d.glob("*.md"):
        seq = _seq_from_name(p.name)
        if seq is not None:
            if len(top_n) < a.n:
                heapq.heappush(top_n, (seq, p))
            elif seq > top_n[0][0]:
                heapq.heapreplace(top_n, (seq, p))

    # Extract in ascending order (heappop gets the smallest first)
    files = [heapq.heappop(top_n)[1] for _ in range(len(top_n))]

    for p in files:
        _print_message(p)
    if not files:
        print(f"(channel '{a.channel}' is empty)")


def cmd_claim(root: Path, a):
    """Atomically claim a task marker file by renaming it (os.replace is atomic).

    Convention: a claimable task is a file `task-<id>.md`. Claiming renames it to
    `task-<id>.CLAIMED-<agent>.md`. If the source is already gone, another agent
    won the race -- exit non-zero so the caller moves on.
    """
    _check_safe_name(a.task, "task")
    if not _TASK_MARKER_RE.fullmatch(a.task):
        raise AgentChatError(
            f"invalid task name (expected task-<id>.md marker): '{a.task}'"
        )
    d = require_channel(root, a.channel)
    src = d / a.task
    dst = d / (Path(a.task).stem + f".CLAIMED-{slugify(a.agent)}.md")
    lock = _acquire_lock(d)
    try:
        if dst.exists():
            die(f"task '{a.task}' already claimed or missing (lost the race)", code=3)
        if not src.is_file():
            die(f"task '{a.task}' already claimed or missing (lost the race)", code=3)
        try:
            os.replace(src, dst)  # atomic on Windows + POSIX within the claim lock
        except FileNotFoundError:
            die(f"task '{a.task}' already claimed or missing (lost the race)", code=3)
    finally:
        _release_lock(lock)
    print(f"claimed {a.task} -> {dst.name}")


# --- argparse ----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chat.py", description="peer agent chat over markdown files"
    )
    p.add_argument(
        "--root", help="chat root dir (default: $AGENT_CHAT_ROOT or ~/agent-chat)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create a channel")
    s.add_argument("channel")
    s.add_argument("--members", help="comma-separated agent names")
    s.add_argument("--topic")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("channels", help="list channels")
    s.set_defaults(func=cmd_channels)

    s = sub.add_parser("roster", help="show a channel's members")
    s.add_argument("channel")
    s.set_defaults(func=cmd_roster)

    s = sub.add_parser(
        "post", help="post a message (body via --body/--body-file/stdin)"
    )
    s.add_argument("channel")
    s.add_argument("--from", dest="sender", required=True)
    s.add_argument("--to", help="recipient agent, or 'all' (default all)")
    s.add_argument("--title", required=True)
    s.add_argument("--reply", type=int, help="seq this replies to")
    s.add_argument("--status", default="discussion")
    s.add_argument("--body")
    s.add_argument("--body-file")
    s.set_defaults(func=cmd_post)

    s = sub.add_parser("read", help="print new messages for an agent (advances cursor)")
    s.add_argument("channel")
    s.add_argument("--as", dest="agent", required=True)
    s.add_argument(
        "--all", action="store_true", help="show entire thread, ignore relevance"
    )
    s.add_argument("--peek", action="store_true", help="do not advance the cursor")
    s.set_defaults(func=cmd_read)

    s = sub.add_parser(
        "wait", help="block (sleep-poll, 0 tokens) until a reply arrives"
    )
    s.add_argument("channel")
    s.add_argument("--as", dest="agent", required=True)
    s.add_argument("--timeout", type=float, default=900.0)
    s.add_argument("--interval", type=float, default=5.0)
    s.set_defaults(func=cmd_wait)

    s = sub.add_parser("peek", help="show last N messages without touching the cursor")
    s.add_argument("channel")
    s.add_argument("-n", type=int, default=3)
    s.set_defaults(func=cmd_peek)

    s = sub.add_parser("claim", help="atomically claim a task-<id>.md marker")
    s.add_argument("channel")
    s.add_argument("task", help="task marker filename, e.g. task-12.md")
    s.add_argument("--as", dest="agent", required=True)
    s.set_defaults(func=cmd_claim)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = root_dir(args.root)
    try:
        args.func(root, args)
    except AgentChatError as e:
        die(str(e))
    except KeyboardInterrupt:
        print(file=sys.stderr)  # print a newline to cleanly break from input prompts
        die("cancelled by user", code=130)


if __name__ == "__main__":
    main()
