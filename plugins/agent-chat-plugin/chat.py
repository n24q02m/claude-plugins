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


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, maxlen: int = 40) -> str:
    s = _NON_ALNUM_RE.sub("-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-")) or "msg"


def die(msg: str, code: int = 1):
    print(f"agent-chat: {msg}", file=sys.stderr)
    raise SystemExit(code)


# --- channel + message primitives -------------------------------------------


def channel_dir(root: Path, channel: str) -> Path:
    if (
        not channel
        or "\0" in channel
        or "/" in channel
        or "\\" in channel
        or channel in (".", "..")
    ):
        die(f"invalid channel name '{channel}'")
    return root / channel


def require_channel(root: Path, channel: str) -> Path:
    d = channel_dir(root, channel)
    if not (d / "_meta.json").exists():
        die(f"channel '{channel}' not found under {root} (run: init {channel})")
    return d


_SEQ_RE = re.compile(r"^(\d+)-")


def _seq_from_name(name: str) -> int | None:
    m = _SEQ_RE.match(name)
    return int(m.group(1)) if m else None


def message_files(chan: Path):
    seq_files = []
    for p in chan.glob("*.md"):
        seq = _seq_from_name(p.name)
        if seq is not None:
            seq_files.append((seq, p))
    seq_files.sort(key=lambda x: x[0])
    return [p for _, p in seq_files]


def parse_frontmatter(path: Path) -> dict:
    """Minimal front-matter reader: the block between the first two '---' lines.

    Values are strings except `to`, normalized to a list ([] == broadcast/all).
    """
    meta: dict = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            if not first_line.startswith("---"):
                return meta

            raw_meta = {}
            closed = False
            for line in f:
                line_stripped = line.strip()
                if line_stripped == "---":
                    closed = True
                    break
                if ":" in line:
                    k, v = line.split(":", 1)
                    raw_meta[k.strip()] = v.strip()

            if not closed:
                return meta

            meta = raw_meta
    except OSError:
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
                die("could not acquire channel seq lock (another poster is stuck?)")
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
    files = message_files(chan)
    return _seq_from_name(files[-1].name) if files else 0


# --- commands ----------------------------------------------------------------


def cmd_init(root: Path, a):
    d = channel_dir(root, a.channel)
    d.mkdir(parents=True, exist_ok=True)
    (d / ".cursors").mkdir(exist_ok=True)
    meta_path = d / "_meta.json"
    if meta_path.exists():
        die(f"channel '{a.channel}' already exists")
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
    print(f"created channel '{a.channel}' at {d}  members={members or '(open)'}")


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
        files = message_files(chan)
        last = "-"
        if files:
            lm = parse_frontmatter(files[-1])
            last = f"#{_seq_from_name(files[-1].name)} {lm.get('from','?')}: {lm.get('title','')[:40]}"
        rows.append(
            (chan.name, ",".join(meta.get("members", [])) or "(open)", len(files), last)
        )
    if not rows:
        print(f"(no channels yet under {root})")
        return
    w = max(len(r[0]) for r in rows)
    print(f"{'CHANNEL'.ljust(w)}  MSGS  MEMBERS / LAST")
    for name, members, n, last in rows:
        print(f"{name.ljust(w)}  {str(n).rjust(4)}  {members}")
        print(f"{' '.ljust(w)}        last: {last}")


def cmd_roster(root: Path, a):
    d = require_channel(root, a.channel)
    meta = json.loads((d / "_meta.json").read_text(encoding="utf-8"))
    print(f"channel : {meta.get('channel')}")
    print(f"topic   : {meta.get('topic') or '(none)'}")
    print(f"members : {', '.join(meta.get('members', [])) or '(open)'}")
    print(f"messages: {len(message_files(d))}")


def _read_body(a) -> str:
    if a.body is not None:
        return a.body
    if a.body_file:
        return Path(a.body_file).read_text(encoding="utf-8")
    # Default: read from stdin so agents can pipe long markdown bodies.
    data = sys.stdin.read()
    if not data.strip():
        die("empty body (pass --body, --body-file, or pipe via stdin)")
    return data


def cmd_post(root: Path, a):
    d = require_channel(root, a.channel)
    body = _read_body(a)
    to = a.to or "all"
    lock = _acquire_lock(d)
    try:
        seq = _next_seq(d)
        fname = f"{seq:04d}-{slugify(a.sender)}-{slugify(a.title)}.md"
        fm = [
            "---",
            f"seq: {seq}",
            f"from: {a.sender}",
            f"to: {to}",
        ]
        if a.reply:
            fm.append(f"reply_to: {a.reply}")
        fm += [
            f"channel: {a.channel}",
            f"ts: {now_iso()}",
            f"status: {a.status}",
            f"title: {a.title}",
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
    for p in message_files(d):
        seq = _seq_from_name(p.name)
        if seq <= cur:
            continue
        meta = parse_frontmatter(p)
        if not a.all and not is_relevant(meta, a.agent):
            continue
        _print_message(p)
        shown += 1
    top = max_seq(d)
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
        for p in message_files(d):
            seq = _seq_from_name(p.name)
            if seq <= cur:
                continue
            meta = parse_frontmatter(p)
            if is_relevant(meta, a.agent):
                found.append(p)
        if found:
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
    files = message_files(d)[-a.n :]
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
    if (
        not a.task
        or "\0" in a.task
        or "/" in a.task
        or "\\" in a.task
        or a.task in (".", "..")
    ):
        die(f"invalid task name '{a.task}'")
    d = require_channel(root, a.channel)
    src = d / a.task
    dst = d / (Path(a.task).stem + f".CLAIMED-{slugify(a.agent)}.md")
    try:
        os.replace(src, dst)  # atomic on Windows + POSIX when same directory
    except FileNotFoundError:
        die(f"task '{a.task}' already claimed or missing (lost the race)", code=3)
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
    args.func(root, args)


if __name__ == "__main__":
    main()
