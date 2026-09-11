# Agent Chat reference

This file holds the detailed operational reference so the loaded `SKILL.md` stays small. It is product documentation, not a second implementation.

## Root and message protocol

A channel is `<root>/<channel>/`. `init` creates `_meta.json`; messages are immutable numbered Markdown files with frontmatter. `read` and successful `wait` advance the caller's cursor. `peek` does not. `post --to all` or omitted `--to` broadcasts. Use one channel per topic and one identity per participant.

Root precedence is `--root` before the subcommand, then `AGENT_CHAT_ROOT`, then `~/agent-chat`. Every participant must point to the same root on a filesystem supporting the package's atomic replacement and locking semantics. The package does not synchronize home/company roots or install a background service.

## Portable surfaces

- Package CLI: `pipx install agent-chat-plugin`, then `agent-chat ...`.
- One-shot package CLI: `uvx --from agent-chat-plugin agent-chat ...`.
- Checkout/plugin CLI: `python "/path/to/agent-chat-plugin/chat.py" ...`.
- Standalone skill bundle: copy `SKILL.md`, `chat.py`, and the complete `agent_chat/` package together.
- Claude Code plugin: keep `.claude-plugin/`, `commands/`, `skills/`, `hooks/`, `chat.py`, and `agent_chat/` together.

PyPI contains the CLI and runtime modules, not the skill, slash command, or hooks. A Python entry point is portable; host lifecycle registration and output interpretation are host-specific. No surface changes host models, credentials, MCP configuration, or provider routing.

## Structured tasks

```text
chat.py task create <channel> <id> --from <agent> --title <title>
chat.py task list <channel>
chat.py task show <channel> <id>
chat.py task claim <channel> <id> --as <agent> --lease-seconds 300
chat.py task renew <channel> <id> --as <agent> --lease-seconds 300
chat.py task done <channel> <id> --as <agent>
chat.py task block <channel> <id> --as <agent>
chat.py task release <channel> <id> --as <agent>
chat.py task recover <channel> <id> --as <agent> --reason "stale session"
chat.py task recover-pending <channel> --as <agent> [--resolve-publication rollback|published]
```

Tasks are JSON records under `<root>/<channel>/tasks/`; claims are owner-bound records under `claims/`. Valid statuses are `open`, `in_progress`, `blocked`, `done`, and `cancelled`. Dependencies must be `done` before claim/transition. Expired claims require explicit recovery and preserve the previous owner, expiry, and reason. A crash marker fails closed until `recover-pending` resolves it. Task failures exit 2 with stable `TASK_*` codes.

## Path locks and state

```text
chat.py lock <channel> <paths...> --as <agent> --lease-seconds 300
chat.py check <channel> <paths...> [--as <agent>]
chat.py unlock <channel> <lock-id-or-path> --as <agent>
chat.py recover <channel> <lock-id-or-path> --as <agent> --reason "stale session"
chat.py recover-pending <channel> --as <agent> [--resolve-publication rollback|published]
chat.py state <channel> [--write] [--json] [--strict]
chat.py compact <channel> [--as <agent>] [--no-audit] [--json] [--strict]
```

Locks normalize workspace-relative paths, reject traversal/symlink escapes and Windows-invalid names, and detect file/file and directory/file overlap. Only the owner unlocks an active lock; stale recovery is explicit. Lock errors use stable `PATH_LOCK_*` codes.

`state` and `compact` derive deterministic `state.md`; compaction atomically writes the derived file, retains all source records, and normally posts one `state.compacted` audit. JSON mode emits one parseable JSON document. State failures use stable `STATE_*` codes.

## Hooks

`hooks/hooks.json` wires `SessionStart`, `UserPromptSubmit`, and `Stop` for Claude Code. The scripts can also run by absolute path in another host only when that host explicitly adapts the lifecycle and output contract.

Environment:

- `AGENT_CHAT_NAME`: participant identity. Prompt/Stop are silent when absent; SessionStart may warn if channels exist.
- `AGENT_CHAT_ROOT`: channel root.
- `AGENT_CHAT_CHANNELS`: optional comma-separated relevant channels. Invalid names are skipped without suppressing valid channels.
- `CLAUDE_PLUGIN_ROOT`: preferred plugin root; otherwise the hook resolves `chat.py` beside its own `hooks/` directory.

Hooks peek only: no cursor writes, body output, replies, task mutations, peer wakeups, provider calls, or synchronization. They print only when unread messages addressed to the current identity or broadcast exist. Notices are bounded to a small stdout budget; idle hooks are silent. Every hook exits zero, including missing roots and per-channel filesystem failures. An unresolved plugin root emits one bounded stderr diagnostic.

Stop output is JSON with one `systemMessage` field. SessionStart and UserPromptSubmit output plain text. Neither output is a claim that the host loaded the plugin natively.

## Adapter-neutral events

```text
chat.py event post <channel> --from <agent> --type capability --harness <host>
chat.py event post <channel> --from <agent> --type status --harness <host> --status ready
chat.py event read <channel> [--type capability|status]
```

Events advertise portable local capabilities/status only. They do not claim MCP, ACP, agent execution, provider access, or native host integration.
