# Agent Chat -- Commands

All commands accept `--root <shared-folder>` before the subcommand. Run `agent-chat <command> --help` or `python chat.py <command> --help` for every flag.

| Surface | Commands | Contract |
|---|---|---|
| Channels and messages | `init`, `channels`, `roster`, `post`, `read`, `wait`, `peek` | Ordered Markdown messages, relevance filtering, and per-agent cursors. |
| Structured tasks | `task create/list/show/update/claim/renew/done/block/release/recover/recover-pending` | Atomic task state, dependency readiness, lease ownership, and explicit recovery. |
| Path coordination | `lock`, `check`, `unlock`, `recover`, `recover-pending` | Exclusive normalized relative paths; overlapping file/directory locks conflict. |
| Derived state | `state`, `compact` | Deterministic `state.md`; authoritative records are never deleted or truncated. |
| Adapter events | `event post`, `event read` | Versioned capability/status JSON carried through ordinary channel messages. |
| Legacy task marker | `claim` | Backward-compatible atomic rename for `task-<id>.md` markers. |

## Minimal coordinated flow

```bash
agent-chat --root ./agent-chat init review --members alice,bob --topic "Review"
agent-chat --root ./agent-chat task create review T-0001 --from alice --title "Inspect API"
agent-chat --root ./agent-chat task claim review T-0001 --as bob --lease-seconds 300
agent-chat --root ./agent-chat lock review src/api.py --as bob --lease-seconds 300
agent-chat --root ./agent-chat task done review T-0001 --as bob
agent-chat --root ./agent-chat unlock review src/api.py --as bob
agent-chat --root ./agent-chat compact review --as bob --strict
```

A task can advance only after every dependency is `done`. An expired lease or lock is never silently stolen; use the explicit recovery command with a reason so the previous owner and expiry remain auditable.
