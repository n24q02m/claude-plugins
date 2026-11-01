# n24q02m Claude Plugins

**Claude Code plugin marketplace for the n24q02m MCP servers -- install web search, memory, Notion, email, Telegram, Godot, code review, and image/video tools in one command.**

[![CI](https://github.com/n24q02m/claude-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/n24q02m/claude-plugins/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://renovatebot.com)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin_marketplace-D97757)](https://code.claude.com/docs/en/plugin-marketplaces)

<!-- BEGIN: AUTO-GENERATED-CROSS-PROMO -->
<details>
  <summary><strong>Sister projects from n24q02m</strong> (click to expand)</summary>

| Project | Tagline | Tag |
|---|---|---|
| [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) | Knowledge graph for token-efficient code reviews -- semantic search and call-... | MCP |
| [better-drive](https://github.com/n24q02m/better-drive) | 2-way Google Drive sync with .driveignore filter — rclone engine, Windows tray | Tooling |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | IMAP/SMTP email for AI agents -- read, send, organize folders, and manage att... | MCP |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Markdown-first Notion for AI agents -- pages, databases, blocks, and comments... | MCP |
| [better-semantic-release](https://github.com/n24q02m/better-semantic-release) | Drop-in python-semantic-release fork with built-in release-safety guards (orp... | Tooling |
| [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) | Telegram for AI agents -- messages, chats, media, and contacts across both bo... | MCP |
| [better-workspace-mcp](https://github.com/n24q02m/better-workspace-mcp) | Google Workspace MCP server (Docs/Drive/Calendar/Gmail/Sheets/Slides/Tasks/Ch... | MCP |
| [claude-plugins](https://github.com/n24q02m/claude-plugins) | Claude Code plugin marketplace for the n24q02m MCP servers -- install web sea... | Marketplace |
| [jules-task-archiver](https://github.com/n24q02m/jules-task-archiver) | Chrome Extension for bulk operations on Jules tasks via batchexecute API -- a... | Tooling |
| [mcp-core](https://github.com/n24q02m/mcp-core) | Shared foundation for building MCP servers -- Streamable HTTP transport, OAut... | MCP |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search and embedded sync. Open, free, unlimi... | MCP |
| [qwen3-embed](https://github.com/n24q02m/qwen3-embed) | Lightweight Qwen3 text embedding and reranking via ONNX Runtime and GGUF | Library |
| [skret](https://github.com/n24q02m/skret) | Secrets without the server. | CLI |
| [tacet](https://github.com/n24q02m/tacet) | A self-distilling neuro-symbolic cascade that amortises LLM cost across knowl... | Tooling |
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
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)



9 MCP servers and a portable Agent Chat coordination plugin for AI coding agents.

**Full documentation: [docs.n24q02m.com](https://docs.n24q02m.com)** — setup and tool references for all 9 servers, Agent Chat coordination, the `hull` foundation, and [Fastretrieval](https://docs.n24q02m.com/reference/fastretrieval/). Libraries and coordination plugins do not gain an MCP transport by appearing in the same documentation site.

## Install

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install <plugin-name>@n24q02m-plugins
```

Or browse all plugins: run `/plugin` and go to the **Discover** tab.

## Plugins

| Plugin | Category | Description | Config (env / userConfig) |
|--------|----------|-------------|----------|
| **wet-mcp** | Research | Web search, content extraction, library docs, media download | All optional: `OPENROUTER_API_KEY`, `SEARCH_BACKENDS`, `TAVILY_API_KEY`, `BRAVE_API_KEY`, `EXA_API_KEY`, `KAGI_API_KEY`, `FIRECRAWL_API_KEY`, `GITHUB_TOKEN` |
| **mnemo-mcp** | Productivity | Persistent AI memory across sessions | All optional: `MNEMO_URL` (Streamable HTTP endpoint of a running mnemo), `MNEMO_TOKEN` (bearer token when that instance uses token or multi auth) |
| **better-notion-mcp** | Productivity | Notion API — 11 composite tools, ~95% coverage | `NOTION_TOKEN` (required) |
| **better-email-mcp** | Communication | Email IMAP/SMTP — multi-account | `EMAIL_CREDENTIALS` (required) |
| **better-telegram-mcp** | Communication | Telegram dual-mode (Bot API + MTProto) — messages, chats, media | `TELEGRAM_BOT_TOKEN` (optional; required for bot mode) |
| **better-code-review-graph** | Development | Knowledge graph for token-efficient code reviews | All optional: `EMBEDDING_MODELS`, `LOCAL_EMBEDDING_MODEL`, `LOCAL_RERANK_MODEL`, `LOCAL_EMBEDDING_DIM`, `LOCAL_EMBEDDING_MODEL_FILE`, `LOCAL_EMBEDDING_POOLING`, `LOCAL_EMBEDDING_NORMALIZE`, `HULL_EMBED_API_KEY`, `HULL_CHAT_API_KEY` |
| **better-workspace-mcp** | Productivity | Google Workspace — 10 domains plus local time helpers, `config`, `help`, and multi-account OAuth | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (both required) |

[Fastretrieval](https://docs.n24q02m.com/reference/fastretrieval/) is the retrieval library used by Wet, Mnemo, and CRG. Install it as a Python dependency, not as a marketplace plugin or MCP endpoint.

## Configuration

When you run `/plugin install`, Claude Code prompts for that plugin's credentials (declared in each plugin's `userConfig`) and stores sensitive values in your system keychain. You can also set them via the `env` block in `~/.claude/settings.local.json`, or `export` them in your shell profile.

`better-notion-mcp`, `better-email-mcp`, and `better-workspace-mcp` require credentials for their upstream APIs. `better-telegram-mcp` needs a bot token only for bot mode. Wet, Mnemo, and CRG preserve local Fastretrieval-based retrieval without provider API keys. Wet web search additionally needs a runnable backend: credential-free DuckDuckGo/Startpage, an external SearXNG endpoint, a configured cloud provider, or a local installation that can run SearXNG.

### Cloud providers (wet-mcp, mnemo-mcp, better-code-review-graph)

Cloud model selection is separate from installing a plugin and is configured on
the machine that runs the server, in `~/.<server>/config.toml`. Do not infer a
fallback chain just because several keys are present.

- Wet and Mnemo use model cells: `[models.embed]`, `[models.rerank]` and
  `[models.chat]`, each with `base_url`, `model` and `api_key`. The environment
  variable `HULL_<TASK>_API_KEY` (for example `HULL_EMBED_API_KEY`) overrides
  the key in the file, and `OPENROUTER_API_KEY` serves the pre-wired default
  cells. An empty embed or rerank cell falls back to local ONNX models.
- CRG uses `[models.chat]` for summaries and `EMBEDDING_MODELS` for embeddings
  (empty means local ONNX); its optional query reranker is selected by
  `LOCAL_RERANK_MODEL`, not a cloud rerank chain.
- Without a chat key, LLM-backed features are switched off rather than failing.
- Empty/local configuration and cloud behavior are server-specific; see
  [Credential setup](https://docs.n24q02m.com/reference/credential-setup/) and
  the [setup references](https://docs.n24q02m.com/servers/).

CRG does not currently implement cloud reranking.

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

### Google Workspace

```
GOOGLE_OAUTH_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<your-client-secret>
```

Create the OAuth client yourself at [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) — type **Desktop app** for the default stdio mode, **Web application** for self-hosted HTTP. The first run opens Google's consent screen once, then reuses the stored refresh token.

## Skills

Most plugins ship skills, invoked in Claude Code as `<plugin>:<skill>`:

| Plugin | Skills |
|--------|--------|
| wet-mcp | `fact-check`, `compare`, `research-topic`, `lock-project-stack` |
| mnemo-mcp | `session-handoff`, `knowledge-audit`, `recall-context`, `memory-commit`, `passport-bootstrap` |
| better-notion-mcp | `organize-database`, `bulk-update` |
| better-email-mcp | `inbox-review`, `follow-up` |
| better-telegram-mcp | `setup-bot`, `channel-post` |
| better-code-review-graph | `review-pr`, `review-delta`, `refactor-check` |

## Other MCP Clients

Each plugin works with any MCP client. Run directly:

**Python plugins** (uvx / pipx / docker):

```bash
uvx --python 3.13 wet-mcp
uvx --python 3.13 mnemo-mcp
uvx --python 3.13 better-telegram-mcp
uvx --python 3.13 better-code-review-graph
```

**TypeScript plugins** (npx / bunx / docker):

```bash
npx -y @n24q02m/better-notion-mcp
npx -y @n24q02m/better-email-mcp
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

## Deployment

The docs site ([docs.n24q02m.com](https://docs.n24q02m.com)) lives in this repo (`docs/`, Astro). It is built and deployed to the Cloudflare Pages project `mcp-n24q02m` by the `deploy-docs` job in [`cd.yml`](.github/workflows/cd.yml), which runs only on `workflow_dispatch` or `repository_dispatch` (`plugin-sync`, `tools-docs-sync`); a push to `main` does not deploy. The old host `mcp.n24q02m.com` redirects (301) to `docs.n24q02m.com`. Pages under `docs/src/content/docs/servers/` are generated at build time by `docs/scripts/sync-plugin-docs.mjs` from the `plugins/<name>/*.md` sources — edit those source files, never the generated tree, and do not deploy the site manually with `wrangler`.

Plugin assets are synced separately: when a server repo cuts a release, [`cd.yml`](.github/workflows/cd.yml) (`plugin-sync`) copies that release tag's `plugin.json`, skills, hooks, and commands into `plugins/<name>/` on `main`, and the docs site redeploys after each `plugin-sync` run, on a manual `workflow_dispatch`, or on a `tools-docs-sync` dispatch from `tools-docs`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0