# n24q02m Claude Plugins

<!-- BEGIN: AUTO-GENERATED-CROSS-PROMO -->
<details>
  <summary><strong>Sister projects from n24q02m</strong> (click to expand)</summary>

| Project | Tagline | Tag |
|---|---|---|
| [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) | Knowledge graph for token-efficient code reviews -- semantic search and call-... | MCP |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | IMAP/SMTP email for AI agents -- read, send, organize folders, and manage att... | MCP |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Composite MCP server for Godot Engine -- 17 composite tools for AI-assisted g... | MCP |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Markdown-first Notion for AI agents -- pages, databases, blocks, and comments... | MCP |
| [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) | Telegram for AI agents -- messages, chats, media, and contacts across both bo... | MCP |
| [claude-plugins](https://github.com/n24q02m/claude-plugins) | Claude Code plugin marketplace for the n24q02m MCP servers -- install web sea... | Marketplace |
| [imagine-mcp](https://github.com/n24q02m/imagine-mcp) | Image and video understanding + generation for AI agents -- across Gemini, Op... | MCP |
| [jules-task-archiver](https://github.com/n24q02m/jules-task-archiver) | Chrome Extension for bulk operations on Jules tasks via batchexecute API -- a... | Tooling |
| [mcp-core](https://github.com/n24q02m/mcp-core) | Shared foundation for building MCP servers -- Streamable HTTP transport, OAut... | MCP |
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

| Plugin | Category | Description | Config (env / userConfig) |
|--------|----------|-------------|----------|
| **wet-mcp** | Research | Web search, content extraction, library docs, media download | All optional: `JINA_AI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`, `GITHUB_TOKEN` |
| **mnemo-mcp** | Productivity | Persistent AI memory across sessions | All optional: `JINA_AI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY` |
| **better-notion-mcp** | Productivity | Notion API — 11 composite tools, ~95% coverage | `NOTION_TOKEN` (required) |
| **better-email-mcp** | Communication | Email IMAP/SMTP — multi-account | `EMAIL_CREDENTIALS` (required) |
| **better-telegram-mcp** | Communication | Telegram dual-mode (Bot API + MTProto) — messages, chats, media | `TELEGRAM_BOT_TOKEN` (optional; required for bot mode) |
| **better-godot-mcp** | Development | Godot Engine — 17 composite tools for game dev | `GODOT_PATH`, `GODOT_PROJECT_PATH` (both optional) |
| **better-code-review-graph** | Development | Knowledge graph for token-efficient code reviews | All optional: `JINA_AI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY` |
| **imagine-mcp** | Multimodal | Image/video understanding + generation across Gemini, OpenAI, Grok | All optional: `XAI_API_KEY` (default provider), `GEMINI_API_KEY`, `OPENAI_API_KEY` |

## Configuration

When you run `/plugin install`, Claude Code prompts for that plugin's credentials (declared in each plugin's `userConfig`) and stores sensitive values in your system keychain. You can also set them via the `env` block in `~/.claude/settings.local.json`, or `export` them in your shell profile.

`better-notion-mcp` and `better-email-mcp` require credentials to function. `better-telegram-mcp` needs a bot token only for bot mode. `wet-mcp`, `mnemo-mcp`, and `better-code-review-graph` run fully locally with no API keys (local ONNX embedding/reranking) — keys only enable optional cloud providers.

### Cloud providers (wet-mcp, mnemo-mcp, better-code-review-graph)

Each provider is a separate, optional env var. None is required:

```
JINA_AI_API_KEY=jina_xxx
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
COHERE_API_KEY=xxx
```

Provider priority (wet-mcp / CRG): embedding Jina AI > Gemini > OpenAI > Cohere > local ONNX; reranking Jina AI > Cohere > local ONNX.

### imagine-mcp

```
XAI_API_KEY=xai-...      # default provider
GEMINI_API_KEY=AIza...   # optional alternative
OPENAI_API_KEY=sk-...    # optional alternative
```

### Telegram

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
```

Required for bot mode (from [@BotFather](https://t.me/BotFather)); leave empty for user mode.

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

### Godot

```
GODOT_PATH=/path/to/godot           # optional; auto-detects from PATH if empty
GODOT_PROJECT_PATH=/path/to/project # optional default project root
```

## Skills

Each plugin ships skills, invoked in Claude Code as `<plugin>:<skill>`:

| Plugin | Skills |
|--------|--------|
| wet-mcp | `fact-check`, `compare`, `research-topic`, `lock-project-stack` |
| mnemo-mcp | `session-handoff`, `knowledge-audit`, `recall-context`, `memory-commit`, `passport-bootstrap` |
| better-notion-mcp | `organize-database`, `bulk-update` |
| better-email-mcp | `inbox-review`, `follow-up` |
| better-telegram-mcp | `setup-bot`, `channel-post` |
| better-godot-mcp | `build-scene`, `debug-issue`, `add-mechanic` |
| better-code-review-graph | `review-pr`, `review-delta`, `refactor-check` |
| imagine-mcp | `image-describe` |

## Other MCP Clients

Each plugin works with any MCP client. Run directly:

**Python plugins** (uvx / pipx / docker):

```bash
uvx --python 3.13 wet-mcp
uvx --python 3.13 mnemo-mcp
uvx --python 3.13 better-telegram-mcp
uvx --python 3.13 better-code-review-graph
uvx --python 3.13 imagine-mcp
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