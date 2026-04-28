# n24q02m Claude Plugins

8 MCP servers for Claude Code, Codex, and other AI coding agents.

## Install

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install <plugin-name>@n24q02m-plugins
```

Or browse all plugins: run `/plugin` and go to the **Discover** tab.

## Plugins

| Plugin | Category | Description | Env Vars |
|--------|----------|-------------|----------|
| **wet-mcp** | Research | Web search, content extraction, media download | `API_KEYS` (optional) |
| **mnemo-mcp** | Productivity | Persistent AI memory across sessions | `API_KEYS` (optional) |
| **better-notion-mcp** | Productivity | Notion API — 10 tools, ~95% coverage | `NOTION_TOKEN` |
| **better-email-mcp** | Communication | Email IMAP/SMTP — multi-account | `EMAIL_CREDENTIALS` |
| **better-telegram-mcp** | Communication | Telegram dual-mode (Bot + MTProto) — messages, chats, media | `TELEGRAM_BOT_TOKEN` |
| **better-godot-mcp** | Development | Godot Engine — 17 composite tools for game dev | `GODOT_PATH` (optional) |
| **better-code-review-graph** | Development | Knowledge graph for code reviews | `API_KEYS` (optional) |
| **imagine-mcp** | Multimodal | Image/video understanding + generation across Gemini, OpenAI, Grok | `GEMINI_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` (any optional) |

## Configuration

After installing, configure env vars in `~/.claude/settings.local.json` under the `env` block, or `export` in your shell profile. Plugins that need credentials (email, telegram, notion stdio) require them to function. Others (wet, mnemo, CRG) work in local mode without API keys.

### Cloud Embedding (wet-mcp, mnemo-mcp, better-code-review-graph)

```
API_KEYS=GOOGLE_API_KEY:xxx,COHERE_API_KEY:yyy
```

### Telegram

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
```

### Email

```
EMAIL_CREDENTIALS=user@gmail.com:app-password
```

Multiple accounts: `user1@gmail.com:pass1,user2@outlook.com:pass2`

### Notion

```
NOTION_TOKEN=ntn_xxx
```

Get your token from [notion.so/my-integrations](https://www.notion.so/my-integrations).

## Skills

Each plugin includes skills (slash commands):

| Plugin | Skills |
|--------|--------|
| wet-mcp | `/fact-check`, `/compare` |
| mnemo-mcp | `/session-handoff`, `/knowledge-audit` |
| better-telegram-mcp | `/setup-bot`, `/channel-post` |
| better-code-review-graph | `/review-delta`, `/review-pr`, `/refactor-check` |
| better-notion-mcp | `/organize-database`, `/bulk-update` |
| better-email-mcp | `/inbox-review`, `/follow-up` |
| better-godot-mcp | `/build-scene`, `/debug-issue`, `/add-mechanic` |

## Other MCP Clients

Each plugin works with any MCP client. Run directly:

**Python plugins** (uvx / pipx / docker):

```bash
uvx --python 3.13 wet-mcp
uvx --python 3.13 mnemo-mcp
uvx --python 3.13 better-telegram-mcp
uvx --python 3.13 better-code-review-graph
uvx imagine-mcp
```

**TypeScript plugins** (npx / bunx / docker):

```bash
npx -y @n24q02m/better-notion-mcp
npx -y @n24q02m/better-email-mcp
npx -y @n24q02m/better-godot-mcp
```

Add to any MCP client's `settings.json`:

```json
{
  "mcpServers": {
    "wet": {
      "command": "uvx",
      "args": ["--python", "3.13", "wet-mcp"]
    }
  }
}
```

## License

MIT
