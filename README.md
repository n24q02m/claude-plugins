# n24q02m Claude Plugins

<!-- BEGIN: AUTO-GENERATED-CROSS-PROMO -->
<details>
  <summary><strong>Sister projects from n24q02m</strong> (click to expand)</summary>

| Project | Tagline | Tag |
|---|---|---|
| [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) | Knowledge graph for token-efficient code reviews -- fixed search, configurabl... | MCP |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | IMAP/SMTP email server for AI agents -- 7 composite tools with multi-account ... | MCP |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Composite MCP server for Godot Engine -- 17 mega-tools for AI-assisted game d... | MCP |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Markdown-first Notion API server for AI agents -- 11 composite tools replacin... | MCP |
| [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) | MCP server for Telegram with dual-mode support: Bot API (httpx) for quick bot... | MCP |
| [claude-plugins](https://github.com/n24q02m/claude-plugins) | Full documentation: mcp.n24q02m.com — unified docs for all 8 servers + the mc... | Marketplace |
| [imagine-mcp](https://github.com/n24q02m/imagine-mcp) | Production-grade MCP server for image and video understanding + generation ac... | MCP |
| [jules-task-archiver](https://github.com/n24q02m/jules-task-archiver) | Chrome Extension for bulk operations on Jules tasks via batchexecute API -- a... | Tooling |
| [mcp-core](https://github.com/n24q02m/mcp-core) | Unified MCP Streamable HTTP 2025-11-25 transport, OAuth 2.1 Authorization Ser... | MCP |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search and embedded sync. Open, free, unlimi... | MCP |
| [qwen3-embed](https://github.com/n24q02m/qwen3-embed) | Lightweight Qwen3 text embedding and reranking via ONNX Runtime and GGUF | Library |
| [skret](https://github.com/n24q02m/skret) | Secrets without the server. | CLI |
| [tacet](https://github.com/n24q02m/tacet) | TACET: a self-distilling neuro-symbolic cascade that amortises LLM cost in kn... | Tooling |
| [web-core](https://github.com/n24q02m/web-core) | Shared web infrastructure package for search, scraping, HTTP security, and st... | Library |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Open-source MCP server for AI agents: web search, content extraction, and lib... | MCP |

</details>
<!-- END: AUTO-GENERATED-CROSS-PROMO -->

## Table of contents

- [Install](#install)
- [Plugins](#plugins)
- [Configuration](#configuration)
- [Skills](#skills)
- [Other MCP Clients](#other-mcp-clients)
- [License](#license)



8 MCP servers for Claude Code, Codex, and other AI coding agents.

**Full documentation: [mcp.n24q02m.com](https://mcp.n24q02m.com)** — unified docs for all 8 servers + the `mcp-core` foundation library. Covers setup methods, modes (stdio / local-relay / remote-relay / remote-oauth), multi-user deployment, and per-server tool reference.

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