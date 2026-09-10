# WET (Web Extended Toolkit) -- Agent Setup Guide

> Plugin install uses stdio mode with local Fastretrieval retrieval. For web search, select credential-free `duckduckgo,startpage`, a keyed provider, optional-key Firecrawl, or a runnable local/external SearXNG backend through `SEARCH_BACKENDS`.
> The previous "Zero-Config Relay" auto-spawn pattern has been removed.

> Give this file to your AI agent to automatically set up wet-mcp.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, no OAuth/HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx/npx hits PATH or Python version issues. |
| **3. Recommended** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, OAuth/relay-form auth, team self-host, claude.ai web compatibility. |

All MCP servers across this stack share this priority hierarchy. `better-godot-mcp` and `better-code-review-graph` default to stdio plugin install and do not provide an owner-hosted relay/OAuth endpoint; Docker stdio and operator self-hosted HTTP remain available as advanced paths.

> **⚠️ Mutually exclusive — pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name — and `npx`/`uvx` ≠ `docker` ≠ HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Option 1: Claude Code Plugin (stdio default)

Plugin install uses **stdio mode**. Fastretrieval supplies local ONNX retrieval without provider keys. `uvx` can search with `SEARCH_BACKENDS=duckduckgo,startpage`, a configured cloud backend, or an external `SEARXNG_URL`; embedded SearXNG needs the prerequisites supplied by a suitable local/source-built Docker installation.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `EMBEDDING_MODELS` | Optional | Explicit CSV embedding selection; managed route: `cohere/embed-v4.0` (paid) |
| `RERANK_MODELS` | Optional | Explicit CSV rerank selection, such as `cohere/rerank-v4.0-fast` (paid); see the managed provider policy before calls |
| `LLM_MODELS` | Optional | Explicit CSV completion selection; managed route: `openrouter/minimax/minimax-m3:free` only |
| `EMBEDDING_API_BASE` | Optional | Custom embedding endpoint; managed Cohere gateway URL ends in `/cohere/v2/embed` |
| `RERANK_API_BASE` | Optional | Custom rerank endpoint; managed Cohere gateway base ends in `/cohere` and the client appends `/v1/rerank` |
| `LLM_API_BASE` | Optional | Provider-appropriate completion endpoint or CF AI Gateway base |
| `JINA_AI_API_KEY` | Optional | Key for explicitly selected public Jina capabilities; not used by the managed Cloudflare route |
| `GEMINI_API_KEY` | Optional | https://aistudio.google.com/apikey |
| `OPENAI_API_KEY` | Optional | https://platform.openai.com/api-keys |
| `OPENROUTER_API_KEY` | Optional | https://openrouter.ai/settings/keys |
| `COHERE_API_KEY` | Optional | https://dashboard.cohere.com/api-keys |
| `GITHUB_TOKEN` | Optional | https://github.com/settings/tokens (bumps GitHub rate limit 60->5000/hr for library docs discovery) |

### Steps

```bash
# Install from marketplace (includes skills: /fact-check, /compare)
/plugin marketplace add n24q02m/claude-plugins
/plugin install wet-mcp@n24q02m-plugins
```

> Other optional env vars (`SEARCH_BACKENDS`, `TAVILY_API_KEY`, `BRAVE_API_KEY`, `EXA_API_KEY`, `BROWSER_BACKENDS`, `SYNC_ENABLED`, etc.) are not part of the `userConfig` prompt; configure them through the client's supported stdio environment settings when needed. Hosted requests instead use the current subject's relay configuration for search chains and provider keys.

Local retrieval and extraction do not require provider keys. Web search still needs a runnable backend; credential-free providers may return upstream challenges or rate limits. Configure only the backend chain the user selected, rather than silently introducing a paid fallback.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Option 2 (Docker stdio) or Option 3 (HTTP) below, DO NOT `/plugin install` this plugin — pick Option 2 or Option 3 instead. All three methods are mutually exclusive (see Method overview).

## Option 2: Docker stdio (fallback)

> **⚠️ Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall wet-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Option 1 instead if you want full plugin features.

Public OCI publication is discontinued. Clone a release tag, build the stdio
target locally, then run it:

```bash
git clone --branch <release-tag> --depth 1 https://github.com/n24q02m/wet-mcp.git
cd wet-mcp
docker build --target stdio -t wet-mcp:local .
docker run -i --rm \
  --name mcp-wet \
  -v wet-data:/data \
  -e JINA_AI_API_KEY \
  -e GEMINI_API_KEY \
  -e OPENAI_API_KEY \
  -e COHERE_API_KEY \
  -e RERANK_MODELS \
  -e BRAVE_API_KEY \
  -e TAVILY_API_KEY \
  -e EXA_API_KEY \
  -e BROWSER_BACKENDS \
  -e GITHUB_TOKEN \
  wet-mcp:local
```

Or as an MCP server config:

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

Stdio mode is the default and works for most personal/single-user scenarios. Consider switching to HTTP mode (Option 3) when you need:

- **claude.ai web compatibility** -- HTTP transport is required to connect plugins to claude.ai web client (stdio only works with desktop clients)
- **One server shared across N Claude Code sessions** -- single daemon serves all sessions instead of spawning a fresh stdio process per session (lower memory, shared cache)
- **Optional non-CF GDrive OAuth** -- eligible local/self-hosted deployments can use the bundled public client; CF-hosted docs storage disables this redundant sync path.
- **Multi-device credential sync** -- self-host the HTTP server once, log in from multiple machines without re-pasting API keys
- **Multi-user team sharing** -- single self-hosted instance supports N users with per-JWT-sub credential isolation
- **Always-on persistent process** -- ideal for webhooks, scheduled agents, or background automation

## Option 3: Docker HTTP (recommended)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall wet-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `wet-mcp:fact-check` skill will no longer be available. Use Option 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1 / Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Self-host with docker-compose

HTTP mode runs as a persistent multi-user server with browser-based credential setup. Eligible non-CF hosts can use the bundled public Google Desktop client for the Drive device-code flow. `DOCS_DB_BACKEND=cf-d1` disables redundant Drive sync, wizard/device-code setup, and auto-sync, even if stale sync settings remain.

From the `wet-mcp` checkout, build the HTTP target and run it:

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

Configure MCP client to connect:

```json
{
  "mcpServers": {
    "wet": {
      "url": "https://wet.example.com/mcp"
    }
  }
}
```

On first call, the client redirects to the relay form. Configure the current subject's models, API bases, matching provider keys, and explicit `SEARCH_BACKENDS` chain. For example, `tavily,duckduckgo,startpage` requires that subject's Tavily key before credential-free fallback; select only user-authorized providers. Hosted requests never inherit operator search/model chains or keys. Only eligible non-CF hosts with sync enabled offer the Drive device-code flow. Each user receives an isolated credential vault keyed by JWT sub.

Follow the [managed provider policy](/reference/relay-flow/#managed-cloudflare-model-configuration)
for Minimax-free completion and paid Cohere retrieval through Cloudflare AI
Gateway. Cloudflare Browser Run (`BROWSER_BACKENDS=cf-browser-rendering`)
provides extraction renderer escalation, not an implicit local browser.
`extract(action="interact")` still requires native Patchright sessions;
the renderer setting does not move interactive sessions to Browser Run.
Do not edit the user's OMP model/profile settings or enable periodic sync as
part of server setup.

### Edge auth: relay password

Public HTTP deployments expose `<your-domain>/authorize` to URL discovery. To prevent random Internet users from accessing the relay form, mint a relay password:

```bash
openssl rand -hex 32
# Save in your skret / .env as:
MCP_RELAY_PASSWORD=<generated-32-byte-hex>
```

Share this password out-of-band (Signal/email/SMS) with anyone you invite to use your server. They will see a login form when first opening `/authorize`; once logged in, the cookie persists 24 hours.

**Single-user dev exception**: If `PUBLIC_URL=http://localhost:8080`, you can leave `MCP_RELAY_PASSWORD` empty to disable the gate. The server logs a warning if you skip the password with a non-localhost `PUBLIC_URL`.

## Environment Variables

Local stdio requires no provider API keys. HTTP authentication, selected cloud providers, and browser/search backends have their own requirements. Preserve the user's chosen local or managed configuration.

### API Keys (Cloud Providers)

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `JINA_AI_API_KEY` | No | -- | Key for explicitly selected public Jina capabilities; not used by the managed Cloudflare route |
| `GEMINI_API_KEY` | No | -- | Google Gemini key: LLM (structured extraction, media analysis) + embedding |
| `GOOGLE_VERTEX_EXPRESS_API_KEY` | No | -- | Vertex AI Express: Gemini via API key, no Service Account. Get it at https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview |
| `OPENAI_API_KEY` | No | -- | Key for explicitly selected OpenAI models |
| `OPENROUTER_API_KEY` | No | -- | Key for explicitly selected OpenRouter models |
| `COHERE_API_KEY` | No | -- | Cohere key: embedding + reranking |
| `BRAVE_API_KEY` | No | -- | Brave Search API key (premium search provider) |
| `TAVILY_API_KEY` | No | -- | Tavily Search API key |
| `EXA_API_KEY` | No | -- | Exa Search API key |
| `KAGI_API_KEY` | No | -- | Required for the `kagi` search backend |
| `FIRECRAWL_API_KEY` | No | -- | Optional for `firecrawl`; absent means a keyless attempt, not guaranteed free service |
| `GITHUB_TOKEN` | No | auto-detect | GitHub token for docs discovery (60 -> 5000 req/hr). Auto-detected from `gh auth token` |

### Embedding and Reranking

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `EMBEDDING_MODELS` | No | empty | Ordered CSV embedding model chain (`provider/model,...`); empty resolves Fastretrieval's local ONNX model manifest |
| `RERANK_MODELS` | No | empty | Ordered CSV rerank model chain (`provider/model,...`); empty resolves Fastretrieval's local ONNX cross-encoder manifest |
| `EMBEDDING_API_BASE` | No | -- | Custom embedding endpoint; managed Cohere gateway URL ends in `/cohere/v2/embed` |
| `RERANK_API_BASE` | No | -- | Custom rerank endpoint; managed Cohere gateway base ends in `/cohere` |
| `EMBEDDING_DIMS` | No | `0` (auto) | Embedding dimensions; custom local models may require `LOCAL_EMBEDDING_DIM` |
| `LOCAL_EMBEDDING_MODEL` | No | -- | Optional BYO local embedding model ID; empty uses Fastretrieval's bundled model manifest |
| `LOCAL_EMBEDDING_DIM` | No | `0` | Required for a BYO local embedding when its model manifest does not provide dimensions |
| `LOCAL_EMBEDDING_POOLING` | No | `MEAN` | Pooling for a BYO local embedding (`MEAN`, `CLS`, `LAST_TOKEN`, or `DISABLED`) |
| `LOCAL_EMBEDDING_NORMALIZE` | No | `true` | Normalize BYO local embedding outputs |
| `LOCAL_RERANK_MODEL` | No | -- | Optional BYO local reranker model ID; empty uses Fastretrieval's bundled model manifest |
| `LOCAL_RERANK_MODEL_FILE` | No | `onnx/model.onnx` | ONNX file path for a BYO local reranker |
| `RERANK_ENABLED` | No | `true` | Enable reranking after search |
| `RERANK_TOP_N` | No | `10` | Return top N results after reranking |

### LLM

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `LLM_MODELS` | No | empty | Ordered CSV LLM model chain (`provider/model,...`); empty leaves optional LLM features disabled |
| `LLM_API_BASE` | No | -- | Provider-appropriate completion endpoint or CF AI Gateway base |

### Legacy model aliases

`EMBEDDING_BACKEND`, `EMBEDDING_MODEL`, `RERANK_BACKEND`, and `RERANK_MODEL` are deprecated and honored for one release. Use the plural `EMBEDDING_MODELS` and `RERANK_MODELS` chains instead.

### Search backends

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `SEARCH_BACKENDS` | No | `searxng` | Ordered CSV chain: `searxng`, `tavily`, `brave`, `exa`, `kagi`, `firecrawl`, `duckduckgo`, `startpage` |
| `WET_AUTO_SEARXNG` | No | `true` | Auto-start bundled SearXNG when the runtime includes its prerequisites; `uvx` plugin environments do not bundle them |
| `DISABLE_LOCAL_SEARCH` | No | `false` | Skip the embedded local SearXNG fallback while retaining external or cloud search backends |
| `WET_SEARXNG_PORT` | No | `41592` | SearXNG port |
| `SEARXNG_URL` | No | `http://localhost:41592` | URL for an external SearXNG deployment |
| `SEARXNG_TIMEOUT` | No | `30` | SearXNG request timeout in seconds |

`duckduckgo` and `startpage` require no credentials and work under `uvx`.
Firecrawl can be attempted without a key. Challenges, errors, or empty results
advance the configured chain; successful credential-free results are not
guaranteed on every network. Public SearXNG remains supported.

### Browser Rendering

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `BROWSER_BACKENDS` | No | empty -> `native` | Ordered CSV render chain: `native`, `browserless`, `cf-browser-rendering` |
| `DISABLE_LOCAL_BROWSER` | No | `false` | Remove `native` from the render chain |
| `BROWSERLESS_URL` | No | -- | Browserless service URL when the chain includes `browserless` |
| `BROWSERLESS_TOKEN` | No | -- | Optional Browserless service token |
| `CF_ACCOUNT_ID` | No | -- | Cloudflare account ID for `cf-browser-rendering` |
| `CF_BROWSER_RENDERING_TOKEN` | No | -- | Cloudflare Browser Rendering API token |

### File Conversion

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `CONVERT_MAX_FILE_SIZE` | No | `104857600` | Max file size for local conversion in bytes (100MB) |
| `CONVERT_ALLOWED_DIRS` | No | -- | Comma-separated paths to restrict local file conversion |

### Storage and Cache

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `CACHE_DIR` | No | `~/.wet-mcp` | Data directory for cache, docs, downloads |
| `DOCS_DB_PATH` | No | `~/.wet-mcp/docs.db` | Docs database location |
| `DOWNLOAD_DIR` | No | `~/.wet-mcp/downloads` | Media download directory |
| `TOOL_TIMEOUT` | No | `120` | Tool execution timeout in seconds (0=no timeout) |
| `WET_CACHE` | No | `true` | Enable/disable web cache |

### Google Drive Sync

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `SYNC_ENABLED` | No | `true` | Enable sync on eligible non-CF hosts; `DOCS_DB_BACKEND=cf-d1` disables it |
| `GOOGLE_DRIVE_CLIENT_ID` | No | bundled public client | OAuth client ID. HTTP mode auto-uses bundled public Desktop client |
| `GOOGLE_DRIVE_CLIENT_SECRET` | No | bundled public secret | OAuth client secret (Desktop public client per Google docs) |
| `SYNC_FOLDER` | No | `wet-mcp` | Google Drive folder name |
| `SYNC_INTERVAL` | No | `300` | Auto-sync interval in seconds (0=manual) |

### General

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `MCP_TRANSPORT` | No | `stdio` | Transport: `stdio` (default) or `http` |
| `PUBLIC_URL` | No | -- | HTTP mode: public URL of the server (required for multi-user OAuth) |
| `MCP_DCR_SERVER_SECRET` | No | -- | HTTP mode: random secret for Dynamic Client Registration JWT signing |

## Authentication

### Stdio Mode (default)

Set provider keys and endpoints directly as environment variables. A stdio `uvx` install still needs a configured SearXNG endpoint or cloud search provider for web search; cloud embedding, LLM, and premium search features activate from their corresponding variables. Credentials live only in the local process environment.

### HTTP Mode (optional, multi-user)

After connecting an MCP client to the HTTP endpoint, the client redirects to the relay form on first call:

1. Open the relay URL in any browser
2. Fill in API keys on the guided form (all optional)
3. If `SYNC_ENABLED=true`, complete the GDrive device-code flow using the bundled public Desktop client (no user OAuth registration needed)
4. Credentials are encrypted per-JWT-sub and isolated per user

Each user receives an isolated credential vault keyed by JWT sub.

## Verification

After setup, verify the server is working by calling the `search` tool:

```
search(action="search", query="test query", limit=3)
```

Expected: returns search results with titles, URLs, and snippets.
