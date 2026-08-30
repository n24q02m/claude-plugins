# WET (Web Extended Toolkit) -- Manual Setup Guide

> **2026-08-30 Update**: Plugin install (Method 1) uses stdio mode. It provides local Fastretrieval embedding/reranking, extraction, and library docs without API keys. Web search needs a configured cloud/SearXNG endpoint or the locally built Docker image that bundles SearXNG.
> The previous "Zero-Config Relay" auto-spawn pattern has been removed.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, no OAuth/HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx/npx hits PATH or Python version issues. |
| **3. Recommended** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, OAuth/relay-form auth, team self-host, claude.ai web compatibility. |

All MCP servers across this stack share this priority hierarchy. Note: 2 plugins (`better-godot-mcp` and `better-code-review-graph`) default to **stdio via plugin install** and do not offer a hosted remote-relay/OAuth mode. They do ship Docker images (`:stdio` and `:http` targets) and support HTTP transport for self-hosting (`MCP_TRANSPORT=http` / `--http`), so Methods 2 and 3 are available as advanced self-host paths -- they are just not the default.

> **⚠️ Mutually exclusive — pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name — and `npx`/`uvx` ≠ `docker` ≠ HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Prerequisites

- **Python 3.13** (3.14+ is NOT supported due to SearXNG incompatibility)
- `uv` or `uvx` installed ([docs](https://docs.astral.sh/uv/getting-started/installation/))
- Docker (optional, for containerized setup)

## Method 1: Plugin Install (stdio default)

For Claude Code users, the plugin approach is the simplest. Plugin marketplace install runs the server in **pure stdio mode**. Fastretrieval's local ONNX registry/runtime provides embedding and reranking without API keys; content extraction and library docs also work without a search provider. Web search requires a configured cloud/SearXNG endpoint or the locally built Docker image that bundles SearXNG.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `RERANK_MODELS` | Optional | CSV rerank model chain such as `jina_ai/jina-reranker-v3`; leave empty for Fastretrieval's local ONNX reranker manifest |
| `JINA_AI_API_KEY` | Optional | https://jina.ai/api-key (highest priority embedding+reranking) |
| `GEMINI_API_KEY` | Optional | https://aistudio.google.com/apikey |
| `OPENAI_API_KEY` | Optional | https://platform.openai.com/api-keys |
| `COHERE_API_KEY` | Optional | https://dashboard.cohere.com/api-keys |
| `GITHUB_TOKEN` | Optional | https://github.com/settings/tokens (bumps GitHub rate limit 60->5000/hr for library docs discovery) |

### Steps

1. Open Claude Code.
2. Install the plugin (Claude Code prompts for `JINA_AI_API_KEY` + `GEMINI_API_KEY` -- press Enter to skip):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install wet-mcp@n24q02m-plugins
   ```
3. Restart Claude Code -- the server starts automatically when CC launches with the values injected.

Without env vars: content extraction, library docs, and Fastretrieval-managed local embedding/reranking work. For web search, configure a cloud/SearXNG backend or use the locally built Docker image; other env vars enable cloud embedding/reranking, LLM analysis, and premium providers.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Method 2 (Docker stdio) or Method 3 (HTTP) below, DO NOT `/plugin install` this plugin — pick Method 2 or Method 3 instead. All three methods are mutually exclusive (see Method overview).

## Method 2: Docker stdio (fallback)

> **⚠️ Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall wet-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Method 1 instead if you want full plugin features.

1. Public OCI publication is discontinued. Clone a release tag and build the
   stdio target locally:
   ```bash
   git clone --branch <release-tag> --depth 1 https://github.com/n24q02m/wet-mcp.git
   cd wet-mcp
   docker build --target stdio -t wet-mcp:local .
   ```

2. Run with environment variables:
   ```bash
   docker run -i --rm \
     --name mcp-wet \
     -v wet-data:/data \
     -e JINA_AI_API_KEY=your_key_here \
     -e GEMINI_API_KEY=your_key_here \
     wet-mcp:local
   ```

3. Or add to your MCP client config:
   ```json
   {
     "mcpServers": {
       "wet": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "--name", "mcp-wet",
           "-v", "wet-data:/data",
           "-e", "JINA_AI_API_KEY",
           "-e", "GEMINI_API_KEY",
           "-e", "GITHUB_TOKEN",
           "wet-mcp:local"
         ]
       }
     }
   }
   ```

## Why upgrade to HTTP mode?

Stdio mode is the default and works for most personal/single-user scenarios. Consider switching to HTTP mode (Method 3 self-host) when you need:

- **claude.ai web compatibility** -- HTTP transport is required to connect plugins to claude.ai web client (stdio only works with desktop clients)
- **One server shared across N Claude Code sessions** -- single daemon serves all sessions instead of spawning a fresh stdio process per session (lower memory, shared cache)
- **Browser-based GDrive OAuth flow** -- HTTP mode performs the Google Device Code flow via the bundled public client; no manual `GOOGLE_DRIVE_CLIENT_ID` setup required
- **Multi-device credential sync** -- self-host the HTTP server once, log in from multiple machines without re-pasting API keys
- **Multi-user team sharing** -- single self-hosted instance supports N users with per-JWT-sub credential isolation
- **Always-on persistent process** -- ideal for webhooks, scheduled agents, or background automation

## Method 3: Docker HTTP (recommended)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall wet-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `wet-mcp:fact-check` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1 / Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Self-host with docker-compose

HTTP mode runs as a persistent multi-user server with browser-based credential setup. GDrive OAuth uses a **bundled public Google Desktop client** (`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`) per Google's official Desktop OAuth pattern -- no user-side OAuth registration is required. Users authenticate via the device-code flow in their browser.

1. From the `wet-mcp` checkout, build the HTTP target and run it:
   ```bash
   docker build --target http -t wet-mcp-http:local .
   docker run -d --name wet-mcp-http \
     -p 8080:8080 \
     -v wet-data:/data \
     -e MCP_TRANSPORT=http \
     -e PUBLIC_URL=https://wet.example.com \
     -e MCP_DCR_SERVER_SECRET=your-random-secret \
     wet-mcp-http:local
   ```

2. Configure your MCP client to connect to the HTTP endpoint:
   ```json
   {
     "mcpServers": {
       "wet": {
         "url": "https://wet.example.com/mcp"
       }
     }
   }
   ```

3. On first call, the client redirects to the relay form. Fill in API keys (all optional) and -- if `SYNC_ENABLED=true` -- complete the GDrive device-code flow in your browser using the bundled public client.

Each user receives an isolated credential vault keyed by JWT sub. No per-user OAuth registration needed.

### Edge auth: relay password

Public HTTP deployments expose `<your-domain>/authorize` to URL discovery. To prevent random Internet users from accessing the relay form, mint a relay password:

```bash
openssl rand -hex 32
# Save in your skret / .env as:
MCP_RELAY_PASSWORD=<generated-32-byte-hex>
```

Share this password out-of-band (Signal/email/SMS) with anyone you invite to use your server. They will see a login form when first opening `/authorize`; once logged in, the cookie persists 24 hours.

**Single-user dev exception**: If `PUBLIC_URL=http://localhost:8080`, you can leave `MCP_RELAY_PASSWORD` empty to disable the gate. The server logs a warning if you skip the password with a non-localhost `PUBLIC_URL`.

## Troubleshooting

### Server fails to start with Python 3.14+

wet-mcp requires Python 3.13 due to SearXNG incompatibility. Always use `--python 3.13` with uvx:

```bash
uvx --python 3.13 wet-mcp
```

### First run takes a long time

On first start, the server downloads:
- SearXNG search engine
- Playwright chromium browser
- ONNX embedding and reranker models (~1.1GB total)

Use the warmup command to pre-download: `config(action="warmup")`

### SearXNG port conflict

If port 41592 is in use, change it:

```bash
export WET_SEARXNG_PORT=41593
```

### Docker volume permissions

If you encounter permission errors with the Docker volume:

```bash
docker run -i --rm -v wet-data:/data --user $(id -u):$(id -g) wet-mcp:local
```

### Embedding model download fails

If ONNX model download fails behind a proxy, use cloud embedding instead by setting any API key (e.g., `GEMINI_API_KEY`).

## Environment Variable Reference

All environment variables are **optional**. See [docs/setup-with-agent.md](setup-with-agent.md#environment-variables) for the complete table.

### Key Variables

| Variable | Default | Description |
|:---------|:--------|:------------|
| `JINA_AI_API_KEY` | -- | Jina AI: search + extraction + embedding + reranking |
| `GEMINI_API_KEY` | -- | Gemini: LLM + embedding (free tier) |
| `GOOGLE_VERTEX_EXPRESS_API_KEY` | -- | Vertex AI Express: Gemini via API key, no Service Account. Get it at https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview |
| `OPENAI_API_KEY` | -- | OpenAI: LLM + embedding |
| `ANTHROPIC_API_KEY` | -- | Anthropic: LLM dispatch for content-selector inference |
| `XAI_API_KEY` | -- | xAI/Grok: LLM dispatch for content-selector inference |
| `COHERE_API_KEY` | -- | Cohere: embedding + reranking |
| `WEB_CORE_LLM_MODEL` | auto-detect | Override the LLM model used for content-selector inference |
| `EMBEDDING_MODELS` | empty | Ordered CSV embedding model chain (`provider/model,...`); empty resolves Fastretrieval's local ONNX model manifest |
| `RERANK_MODELS` | empty | Ordered CSV rerank model chain (`provider/model,...`); empty resolves Fastretrieval's local ONNX cross-encoder manifest |
| `LLM_MODELS` | empty | Ordered CSV LLM model chain (`provider/model,...`); empty leaves optional LLM features disabled |
| `EMBEDDING_DIMS` | `0` (auto) | Embedding dimensions; custom local models may require `LOCAL_EMBEDDING_DIM` |
| `LOCAL_EMBEDDING_MODEL` | -- | Optional BYO local embedding model ID; empty uses Fastretrieval's bundled model manifest |
| `LOCAL_EMBEDDING_DIM` | `0` | Required for a BYO local embedding when its model manifest does not provide dimensions |
| `LOCAL_EMBEDDING_POOLING` | `MEAN` | Pooling for a BYO local embedding (`MEAN`, `CLS`, `LAST_TOKEN`, or `DISABLED`) |
| `LOCAL_EMBEDDING_NORMALIZE` | `true` | Normalize BYO local embedding outputs |
| `LOCAL_RERANK_MODEL` | -- | Optional BYO local reranker model ID; empty uses Fastretrieval's bundled model manifest |
| `LOCAL_RERANK_MODEL_FILE` | `onnx/model.onnx` | ONNX file path for a BYO local reranker |
| `BRAVE_API_KEY` | -- | Brave Search API key (premium search) |
| `TAVILY_API_KEY` | -- | Tavily search API key |
| `EXA_API_KEY` | -- | Exa search API key |
| `GITHUB_TOKEN` | auto-detect | GitHub token for docs discovery |
| `SEARCH_BACKENDS` | `searxng` | Ordered CSV search chain: `searxng`, `tavily`, `brave`, `exa` |
| `WET_AUTO_SEARXNG` | `true` | Auto-start bundled SearXNG when the runtime includes its prerequisites; `uvx` plugin environments do not bundle them |
| `DISABLE_LOCAL_SEARCH` | `false` | Skip the embedded local SearXNG fallback while retaining external or cloud search backends |
| `BROWSER_BACKENDS` | empty -> `native` | Ordered CSV render chain: `native`, `browserless`, `cf-browser-rendering` |
| `SYNC_ENABLED` | `true` | Enable Google Drive sync |
| `LOG_LEVEL` | `INFO` | Logging level |

### Backend Selection

- **Embedding, reranking, and LLM**: use the ordered `EMBEDDING_MODELS`, `RERANK_MODELS`, and `LLM_MODELS` chains; provider keys are inferred from each `provider/model` prefix.
- **Local model overrides**: use `LOCAL_EMBEDDING_MODEL` / `LOCAL_RERANK_MODEL`; built-in IDs resolve through Fastretrieval's model manifest, while custom embedding IDs require the matching local metadata variables above.
- **Legacy aliases**: `EMBEDDING_BACKEND`, `EMBEDDING_MODEL`, `RERANK_BACKEND`, and `RERANK_MODEL` are deprecated and honored for one release; migrate to the plural model chains.
- **Browser rendering**: `BROWSER_BACKENDS` escalates in listed order; an empty chain uses the local `native` browser.
- **Search**: `SEARCH_BACKENDS` falls back in listed order. The source-built Docker image can bundle the local SearXNG leg; `uvx` plugin installs require a configured SearXNG endpoint or cloud provider.
