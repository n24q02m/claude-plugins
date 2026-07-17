---
name: agent-chat
description: Use when two or more agent sessions (Claude Code or other tools, same machine or peers) must coordinate through markdown files in a shared folder instead of one supervisor driving subagents — group chat, blackboard, mailbox/inbox, multi-session handoff, or an agent-chat/ directory. Triggers include peer agents, N sessions sharing a folder, waiting for another session's reply, atomic task claiming, and needing multiple separate group chats/channels.
---

# agent-chat

## Overview

Peer agent sessions coordinate by exchanging **markdown files in shared channel folders** — no supervisor, no message broker, no RAM shared between them. Each channel is one "group chat". The whole thread is plain markdown: git-committable, human-readable, replayable. A crashed session loses nothing — the files are the state.

One CLI (`chat.py`, Python stdlib only) runs identically on Windows, WSL and Linux. `wait` blocks with a sleep-poll loop, so **an agent waiting for a reply burns zero model tokens** while idle.

**Core principle:** talk through files, not through each other. Summaries as artifacts, not full transcripts passed back and forth.

## When to use

- Multiple `claude` sessions (or Cursor/Codex/OpenCode) working the same problem as equals.
- One session needs another to do something, then waits for the result.
- You want an auditable record of an agent negotiation.
- You need **several independent group chats** (one per topic/team) — make one channel each.

**When NOT to use:** a single agent with cheap subagents is cheaper and simpler — this pattern trades tokens for parallelism, fault tolerance, and auditability. If token budget is tight, use only the async/handoff path (post a summary at end of session; the next session reads it) — that mode costs almost nothing.

## Quick reference

As a Claude Code plugin, run `python ${CLAUDE_PLUGIN_ROOT}/chat.py <cmd>` (standalone: `python chat.py <cmd>`). Root = `$AGENT_CHAT_ROOT` or `~/agent-chat` (override with `--root`).

| Do this | Command |
|---|---|
| Create a group chat | `chat.py init review --members alice,bob --topic "..."` |
| List all group chats | `chat.py channels` |
| Post a message | `chat.py post review --from alice --to bob --title "Schema v0.2" --body-file msg.md` |
| Broadcast to the group | `chat.py post review --from alice --to all --title "..."` (or omit `--to`) |
| Read what's new for me | `chat.py read review --as bob` |
| Wait for a reply (0 tokens) | `chat.py wait review --as alice --timeout 900` |
| Peek recent, keep cursor | `chat.py peek review -n 3` |
| Claim a task atomically | `chat.py claim work task-12.md --as bob` |

`--reply <seq>` threads a message to an earlier one. `python chat.py <cmd> --help` for all flags.

In a Claude Code session, `/agent-chat` runs the read/reply loop for you using `$AGENT_CHAT_NAME`; a `SessionStart` hook also peeks your inbox and prints unread counts.

## Folder layout

```
<root>/
  review/                     # one channel = one group chat
    _meta.json                   # members, topic, created
    0001-alice-schema-draft.md # NNNN-<from>-<slug>.md, frontmatter + body
    0002-bob-schema-review.md
    .cursors/bob.txt           # per-agent "last seq read"
  deploy/                    # a SECOND group chat, separate seq space
    ...
```

Message frontmatter: `seq, from, to, reply_to?, channel, ts, status, title`. `to: all` (or omitted) = broadcast.

## Protocol (the rules each session follows)

1. **One channel per topic/team.** Don't cram everything into one folder — that was the prototype's failure. `channels` to discover, `init` to open a new group.
2. **Claim before you act.** Use `claim` (atomic rename) or self-address a message before starting shared work. Lost the race (exit 3)? Move on — someone else has it.
3. **Message, don't chat.** To ask a peer for something, `post` a file addressed `--to them`, then do other work or `wait`. Don't stream chatter.
4. **Wait, don't poll with the LLM.** Use `wait` — it sleeps in-process. Never write a `while` loop that re-invokes the model to "check the folder" (millions of wasted tokens).
5. **Read since your cursor.** `read --as you` shows only messages newer than your cursor and addressed to you or the group, then advances it. Don't re-ingest the whole thread each turn.
6. **Reply in a new file.** Never edit another agent's message file (stale-context corruption). Post a new one with `--reply <seq>`.

## Token economics

Two modes from the same tool:
- **Live swarm** — N sessions running concurrently, `wait`-ing on each other. Higher total tokens; you buy wall-clock parallelism + fault tolerance. For abundant-budget runs.
- **Async handoff / audit** — post a summary when a session ends; the next session (or another tool) `read`s it. Nearly free — usable even under a tight budget.

The savings vs naive peer messaging are real and structural: `wait` (idle = 0 tokens), summary artifacts instead of full-history passing, cursor reads instead of full-folder rescans, and channel-scoped reads (only your groups).

## Common mistakes

| Mistake | Fix |
|---|---|
| `while true; do read; done` in the LLM loop | Use `wait` — it blocks in-process, no tokens. |
| Two sessions grab the same task | Use `claim` (atomic) — never eyeball the board. |
| Everything in one folder | One channel per topic; `init` more. |
| Editing a peer's message to "reply" | Post a new file with `--reply`. |
| Manually numbering files (`-11` twice) | Always `post` — it allocates seq under a lock. |

## Cross-platform

Pure stdlib; no `inotify`/`fswatch` dependency. `wait` uses sleep-polling (default 5s) so it works the same on Windows (no inotify), WSL, and Linux. Atomic ops use `os.mkdir` (seq lock) and `os.replace` (claim), both atomic on NTFS and POSIX.
