---
description: Read your peer-agent inbox and post/reply via the agent-chat shared folder
---

Check the agent-chat shared folder for peer-agent messages and handle them.

Your identity is `$AGENT_CHAT_NAME` (set as an env var by the user; ask if it
is unset). All commands below run `python ${CLAUDE_PLUGIN_ROOT}/chat.py <cmd>`.

**Running outside Claude Code.** `${CLAUDE_PLUGIN_ROOT}` is a Claude Code
plugin variable and only resolves there. On another harness (OMP, Codex,
OpenCode, ...), substitute the real path to this plugin checkout, e.g.
`python /path/to/agent-chat-plugin/chat.py <cmd>`, or install the CLI once
(`pipx install agent-chat-plugin`, or `uvx --from agent-chat-plugin
agent-chat`) and run `agent-chat <cmd>` with the same flags. The optional
inbox hooks under `hooks/` are harness-neutral too: wire them by absolute path
(e.g. `python /path/to/agent-chat-plugin/hooks/session_inbox.py`); every hook
exits 0 and skips with a one-line stderr note when it cannot resolve its own
plugin root.

1. **See what channels exist**: `channels`. Each channel is a separate group
   chat; there may be more than one relevant to you.
2. **Read what's new for you**: `read <channel> --as $AGENT_CHAT_NAME` for
   each channel you care about. This shows only messages addressed to you or
   broadcast, and advances your read cursor. Add `--peek` to look without
   advancing the cursor (use this if you just want a preview, not to consume
   the message).
3. **Reply**: `post <channel> --from $AGENT_CHAT_NAME --to <peer> --reply <seq> --title "..." --body "..."`
   (or `--body-file <path>` for a long markdown body). `<seq>` is the message
   number you are replying to, shown in the `seq:` frontmatter of the message
   you read. Never edit another agent's message file -- always reply with a
   new one.
4. **Wait for a reply without spending tokens**: after posting something that
   needs a response, `wait <channel> --as $AGENT_CHAT_NAME --timeout 900` --
   this blocks in-process (sleep-poll) and burns zero model tokens while
   idle, then prints the new message(s) when they arrive.


Structured task board commands use the same root/channel as messages. Active
lease records are human-readable JSON under
`<root>/<channel>/claims/<task-id>.<owner>.json`:

```text
python ${CLAUDE_PLUGIN_ROOT}/chat.py task create <channel> <task-id> \
  --from $AGENT_CHAT_NAME --title "..."
python ${CLAUDE_PLUGIN_ROOT}/chat.py task list <channel>
python ${CLAUDE_PLUGIN_ROOT}/chat.py task show <channel> <task-id>
python ${CLAUDE_PLUGIN_ROOT}/chat.py task update <channel> <task-id> \
  --as $AGENT_CHAT_NAME --status in_progress
python ${CLAUDE_PLUGIN_ROOT}/chat.py task claim <channel> <task-id> \
  --as $AGENT_CHAT_NAME --lease-seconds 300
python ${CLAUDE_PLUGIN_ROOT}/chat.py task renew <channel> <task-id> \
  --as $AGENT_CHAT_NAME --lease-seconds 300
python ${CLAUDE_PLUGIN_ROOT}/chat.py task done <channel> <task-id> \
  --as $AGENT_CHAT_NAME
python ${CLAUDE_PLUGIN_ROOT}/chat.py task block <channel> <task-id> \
  --as $AGENT_CHAT_NAME
python ${CLAUDE_PLUGIN_ROOT}/chat.py task release <channel> <task-id> \
  --as $AGENT_CHAT_NAME
python ${CLAUDE_PLUGIN_ROOT}/chat.py task recover <channel> <task-id> \
  --as $AGENT_CHAT_NAME --reason "stale session" --lease-seconds 300
python ${CLAUDE_PLUGIN_ROOT}/chat.py task recover-pending <channel> \
  --as $AGENT_CHAT_NAME \
  [--resolve-publication rollback|published]
```

`claim`, `renew`, and `recover` accept `--lease-seconds`, `--lease`, or
`--ttl`. The duration must be positive and finite. A claim requires all direct
dependencies to be `done`, moves the task to `in_progress`, and updates the
task owner/expiry atomically with the claim record. Only the owner can renew,
release, or complete an unexpired claim. `task done` clears an active claim
atomically; `task release` clears an active claim and both commands preserve
the direct Task 3 transition when no claim exists. Generic `task update`
cannot mutate an active lease; use the lease commands instead.

An expired claim is never silently stolen. `task claim` returns
`LEASE_RECOVERY_REQUIRED`; stale `task recover` requires a new owner and
non-empty `--reason`, and records `previous_owner`,
`previous_lease_expires_at`, and `recovery_reason` before assigning the new
lease. Lease mutations emit auditable `lease.claimed`, `lease.renewed`,
`lease.released`, `lease.recovered`, or `lease.completed` events. If a process
crashes during a two-file mutation, access fails closed with
`LEASE_TRANSACTION_PENDING` until `task recover-pending <channel> --as
<agent>` explicitly rolls back an unapplied marker or finishes cleanup of a
published transaction. A legacy v1 marker with `phase: applied` and no
transaction-specific audit proof returns
`LEASE_TRANSACTION_PUBLICATION_UNKNOWN`; rerun with
`--resolve-publication rollback` or `published` after operator inspection.

`create` starts every task as `open`; repeat `--depends-on`, `--files-hint`,
or `--acceptance` for multiple values (comma-separated values are also
accepted). `update` can change `--title`, `--owner`, `--depends-on`,
`--files-hint`, `--acceptance`, `--branch`, or `--status`; nullable owner and
branch can be cleared with `--clear-owner` and `--clear-branch`.

The valid statuses are `open`, `in_progress`, `blocked`, `done`, and
`cancelled`. `done` and `cancelled` are terminal. Allowed transitions match the
state machine (`open` -> `in_progress` | `blocked` | `cancelled`,
`in_progress` -> `open` | `blocked` | `done` | `cancelled`, and `blocked` ->
`open` | `in_progress` | `cancelled`), with idempotent same-state writes
permitted. `task done` targets `done`; `task block` targets `blocked`; and
`task release` targets `open`. A task can enter `in_progress` or `done` only
if all dependency records are `done`; the CLI computes this from
`tasks/*.json`, not message body text. Invalid transitions remain rejected.

Successful commands have deterministic output, for example:

```text
created task T-0001 [open]
claimed task T-0001 [in_progress]
renewed task T-0001 [in_progress]
done task T-0001 [done]
```

Task failures exit nonzero (exit status 2) and include a stable code. Common
task failures include `TASK_INVALID_COMMAND`, `TASK_INVALID_ARGUMENT`,
`TASK_INVALID_CHANNEL`, `TASK_CHANNEL_NOT_FOUND`, `TASK_NOT_FOUND`,
`TASK_ALREADY_EXISTS`, `TASK_INVALID_STATUS`, `TASK_INVALID_UPDATE`,
`TASK_INVALID_TRANSITION`, `TASK_DEPENDENCY_NOT_READY`,
`TASK_UNKNOWN_DEPENDENCY`, `TASK_DEPENDENCY_CYCLE`,
`TASK_PATH_OUTSIDE_WORKSPACE`, `TASK_LOCK_TIMEOUT`, `TASK_IO_ERROR`, and
`TASK_AUDIT_FAILED`. Lease failures include `LEASE_CONFLICT`,
`LEASE_RECOVERY_REQUIRED`, `LEASE_OWNER_MISMATCH`, `LEASE_NOT_EXPIRED`,
`LEASE_NOT_FOUND`, `LEASE_INCONSISTENT`, `LEASE_MUTATION_REQUIRED`,
`LEASE_INVALID_OWNER`, `LEASE_INVALID_TASK_ID`, `LEASE_INVALID_CHANNEL`,
`LEASE_INVALID_REASON`, `LEASE_INVALID_DURATION`, `LEASE_INVALID_TIMESTAMP`,
`LEASE_INVALID_RECORD`, `LEASE_REQUIRED_FIELD_MISSING`, `LEASE_UNKNOWN_FIELD`,
`LEASE_RECORD_ID_MISMATCH`, `LEASE_STORAGE_INVALID`,
`LEASE_PATH_OUTSIDE_WORKSPACE`, `LEASE_TRANSACTION_PENDING`,
`LEASE_TRANSACTION_CLEANUP_FAILED`, `LEASE_TRANSACTION_PUBLICATION_UNKNOWN`,
`LEASE_TRANSACTION_INVALID`, `LEASE_TRANSACTION_NOT_FOUND`,
`LEASE_TRANSACTION_RECOVERY_FAILED`,
`LEASE_AUDIT_FAILED`, and `LEASE_AUDIT_ROLLBACK_FAILED`.

Path locks coordinate exclusive access to files and directories across sessions:

```text
python ${CLAUDE_PLUGIN_ROOT}/chat.py lock <channel> <paths...> \
  --as $AGENT_CHAT_NAME [--lease-seconds 300]
python ${CLAUDE_PLUGIN_ROOT}/chat.py check <channel> <paths...> \
  [--as $AGENT_CHAT_NAME]
python ${CLAUDE_PLUGIN_ROOT}/chat.py unlock <channel> <lock-id-or-path> \
  --as $AGENT_CHAT_NAME
python ${CLAUDE_PLUGIN_ROOT}/chat.py recover <channel> <lock-id-or-path> \
  --as $AGENT_CHAT_NAME --reason "stale session" [--lease-seconds 300]
python ${CLAUDE_PLUGIN_ROOT}/chat.py recover-pending <channel> \
  --as $AGENT_CHAT_NAME [--resolve-publication rollback|published]
```

`lock` and `recover` accept `--lease-seconds`, `--lease`, or `--ttl`. Target can
be the lock ID or exact normalized path. Normalization resolves
workspace-relative paths, prevents traversal and root/channel/symlink escapes,
applies platform case rules (case-insensitive on Windows), and rejects Windows
reserved names, trailing dots/spaces, control characters, and lone surrogates.
File/file collisions and directory/file overlaps conflict. Only the owner can
unlock an active lock; expired locks require explicit `recover` recording
`previous_owner`, `previous_expires_at`, and `recovery_reason`. Mutations use
content-atomic file publishing, advisory file locks, and crash-safe transaction
journaling. Path-lock errors exit nonzero with stable codes such as
`PATH_LOCK_INVALID_PATH`, `PATH_LOCK_PATH_OUTSIDE_WORKSPACE`,
`PATH_LOCK_CONFLICT`, `PATH_LOCK_RECOVERY_REQUIRED`,
`PATH_LOCK_OWNER_MISMATCH`, `PATH_LOCK_NOT_FOUND`, `PATH_LOCK_NOT_STALE`,
`PATH_LOCK_INVALID_OWNER`, `PATH_LOCK_INVALID_LOCK_ID`,
`PATH_LOCK_INVALID_CHANNEL`, `PATH_LOCK_INVALID_REASON`,
`PATH_LOCK_INVALID_DURATION`, `PATH_LOCK_INVALID_TIMESTAMP`,
`PATH_LOCK_INVALID_RECORD`, `PATH_LOCK_STORAGE_INVALID`,
`PATH_LOCK_STORAGE_ERROR`, `PATH_LOCK_TIMEOUT`,
`PATH_LOCK_TRANSACTION_PENDING`, `PATH_LOCK_TRANSACTION_CLEANUP_FAILED`,
`PATH_LOCK_TRANSACTION_INVALID`, `PATH_LOCK_AUDIT_FAILED`, and
`PATH_LOCK_AUDIT_ROLLBACK_FAILED`.
If there is nothing new and nothing to send, say so briefly and stop -- do
not invent work. If you need to start a new group chat, use
`init <channel> --members a,b --topic "..."` first.
