# Agent Chat -- Setup

Agent Chat requires Python 3.8 or newer and a shared local or network folder. It needs no API key, account, daemon, or MCP client configuration.

## Portable CLI/Skill

Run the published package without installing it globally:

```bash
uvx --from agent-chat-plugin agent-chat --help
```

Or clone the repository and invoke the stdlib-only entry point directly:

```bash
python chat.py --root ./agent-chat init review --members alice,bob --topic "Review"
python chat.py --root ./agent-chat post review --from alice --title "Ready" --body "Starting review."
python chat.py --root ./agent-chat read review --as bob
```

On Windows, use a normal path such as `%USERPROFILE%\agent-chat`. On POSIX, use `$HOME/agent-chat`. Every participant must point `--root` or `AGENT_CHAT_ROOT` at the same folder. Do not place credentials or private transcript bodies in channel metadata.

To install the Skill in a harness, copy `skills/agent-chat/SKILL.md` through that harness's documented Skill mechanism. A copied Skill plus CLI access is portable support, not evidence of native lifecycle integration.

## Claude Code plugin adapter

For users who explicitly choose the Claude Code marketplace adapter:

```text
/plugin marketplace add n24q02m/claude-plugins
/plugin install agent-chat-plugin@n24q02m-plugins
```

Set `AGENT_CHAT_NAME`, `AGENT_CHAT_ROOT`, and optionally `AGENT_CHAT_CHANNELS` in the plugin configuration. The hooks only post and surface filesystem events; they never approve or execute work.

Do not add an MCP configuration for Agent Chat. It does not expose an MCP server.
