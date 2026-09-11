---
name: agent-chat
description: Coordinate peer sessions through markdown channels with portable CLI, tasks, leases, locks, and zero-token waits.
---

# Agent Chat

Use this plugin skill when peer sessions need an auditable shared-folder channel. Agent Chat is a dependency-free coordination data layer. It does not execute agents, call an LLM/provider, relay MCP traffic, wake peers, or synchronize machines.

## Commands

```text
python "${CLAUDE_PLUGIN_ROOT}/chat.py" channels
python "${CLAUDE_PLUGIN_ROOT}/chat.py" init review --members alice,bob --topic "..."
python "${CLAUDE_PLUGIN_ROOT}/chat.py" read review --as "$AGENT_CHAT_NAME"
python "${CLAUDE_PLUGIN_ROOT}/chat.py" post review --from "$AGENT_CHAT_NAME" --to bob --title "..." --body "..."
python "${CLAUDE_PLUGIN_ROOT}/chat.py" wait review --as "$AGENT_CHAT_NAME" --timeout 900
```

Use `agent-chat` after `pipx install agent-chat-plugin`, `uvx --from agent-chat-plugin agent-chat ...` for one-shot package use, or an absolute checkout path outside Claude Code. Always ship `chat.py` with the complete `agent_chat/` package; PyPI does not install this skill, slash command, or hooks.

Global `--root` belongs before the subcommand. Root precedence is `--root`, `AGENT_CHAT_ROOT`, then `~/agent-chat`. Set a distinct `AGENT_CHAT_NAME` per participant; separate host roots are not synchronized.

## Tasks and state

Use structured tasks for durable work and explicit ownership:

```text
chat.py task create review T-0001 --from alice --title "Implement schema"
chat.py task claim review T-0001 --as alice --lease-seconds 300
chat.py task renew review T-0001 --as alice --lease-seconds 300
chat.py task done review T-0001 --as alice
chat.py task recover review T-0001 --as bob --reason "stale session"
chat.py lock review src/schema.py --as alice --lease-seconds 300
chat.py check review src/schema.py
chat.py unlock review src/schema.py --as alice
chat.py state review --json
chat.py compact review --as alice --json
```

Claims and path locks are owner-bound and crash-safe. Expired work requires explicit recovery; no command silently steals a lease. `state.md` is derived, never authoritative. Compaction retains all messages, tasks, claims, locks, and cursors.

## Hooks and host portability

`hooks/hooks.json` registers optional Claude Code lifecycle hooks. They are relevant-only, read-only peeks:

- SessionStart/UserPromptSubmit: bounded plain-text unread notice.
- Stop: bounded Claude-compatible `systemMessage` JSON unread notice.
- No unread relevant messages: empty stdout.
- Missing identity: prompt/stop silent; SessionStart may warn when channels exist.
- `AGENT_CHAT_CHANNELS` restricts the scan; malformed configured names are skipped independently.
- Hooks prefer non-empty `CLAUDE_PLUGIN_ROOT`, then resolve `chat.py` beside `hooks/`; unresolved roots emit one stderr note and exit zero.

See `reference.md` in this skill directory for event schemas, recovery codes, and host-specific boundaries.
