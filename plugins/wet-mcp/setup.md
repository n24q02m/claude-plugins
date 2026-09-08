# WET (Web Extended Toolkit) -- Manual Setup Guide

> Plugin install uses stdio mode with local Fastretrieval retrieval. For web search, select credential-free `duckduckgo,startpage`, a keyed provider, optional-key Firecrawl, or a runnable local/external SearXNG backend through `SEARCH_BACKENDS`.
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

For Claude Code users, plugin marketplace install runs the server in **pure stdio mode**. Fastretrieval supplies local ONNX retrieval without provider keys. `uvx` can search with `SEARCH_BACKENDS=duckduckgo,startpage`, a configured cloud backend, or an external `SEARXNG_URL`; embedded SearXNG needs the prerequisites supplied by a suitable local/source-built Docker installation.

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

1. Open Claude Code.
2. Install the plugin (skip optional model/key prompts to keep local retrieval):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install wet-mcp@n24q02m-plugins
   ```
3. Restart Claude Code -- the server starts automatically when CC launches with the values injected.

Local retrieval and extraction do not require provider keys. Web search still needs a runnable backend. Credential-free providers can be challenged or rate-limited by upstream sites; they do not guarantee the same availability as a keyed service.

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
- **Optional non-CF GDrive OAuth** -- eligible local/self-hosted deployments can use the bundled public client; CF-hosted docs storage disables this redundant sync path.
- **Multi-device credential sync** -- self-host the HTTP server once, log in from multiple machines without re-pasting API keys
- **Multi-user team sharing** -- single self-hosted instance supports N users with per-JWT-sub credential isolation
- **Always-on persistent process** -- ideal for webhooks, scheduled agents, or background automation

## Method 3: Docker HTTP (recommended)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall wet-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `wet-mcp:fact-check` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1 / Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Self-host with docker-compose

HTTP mode runs as a persistent multi-user server with browser-based credential setup. Eligible non-CF hosts can use the bundled public Google Desktop client for the Drive device-code flow; no client credential needs to be copied into this guide. `DOCS_DB_BACKEND=cf-d1` disables redundant Drive sync, wizard/device-code setup, and auto-sync, even if stale sync settings remain.

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

3. On first call, the client redirects to the relay form. Configure the current subject's model fields, provider API bases, matching keys, and explicit `SEARCH_BACKENDS` chain. For example, `tavily,duckduckgo,startpage` uses that subject's Tavily key before credential-free providers; choose only the providers the user authorized. Only eligible non-CF hosts with sync enabled offer the Google Drive device-code flow.

Each user receives an isolated credential vault keyed by JWT sub. Hosted search chains and provider credentials come from that vault, not operator environment defaults; an empty subject configuration does not inherit another account's keys. No per-user OAuth registration needed.

For the managed Cloudflare route, follow the [Minimax-free and paid Cohere
configuration policy](/reference/relay-flow/#managed-cloudflare-model-configuration).
Use `BROWSER_BACKENDS=cf-browser-rendering` for Cloudflare Browser Run extraction
renderer escalation, with `CF_ACCOUNT_ID` and `CF_BROWSER_RENDERING_TOKEN`
supplied by the operator. This does not offload `extract(action="interact")`:
that action uses native Patchright browser sessions.
Public local browser and SearXNG support remain available independently;
they are not the managed personal Wet setup.

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

The resources downloaded depend on the selected runtime and backends. Local
embedding/reranker models and a native browser may need initial downloads.
`uvx` does not auto-install a runnable embedded SearXNG service; select a
credential-free/cloud backend or an external `SEARXNG_URL` instead.

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

If local model download fails behind a proxy, fix artifact access or explicitly configure a supported cloud embedding model, matching key, and API base. Provider credentials alone are not proof that the intended route is active; obtain spending authorization before paid calls.

## Environment Variable Reference

Local stdio needs no provider API keys; HTTP, cloud providers, and optional backends have their own requirements. See the [agent setup reference](/servers/wet-mcp/setup-with-agent/#environment-variables) for the complete table.

### Key Variables

| Variable | Default | Description |
|:---------|:--------|:------------|
| `JINA_AI_API_KEY` | -- | Jina AI: search + extraction + embedding + reranking |
| `GEMINI_API_KEY` | -- | Gemini: LLM + embedding (free tier) |
| `GOOGLE_VERTEX_EXPRESS_API_KEY` | -- | Vertex AI Express: Gemini via API key, no Service Account. Get it at https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview |
| `OPENAI_API_KEY` | -- | OpenAI: LLM + embedding |
| `OPENROUTER_API_KEY` | -- | Key for explicitly selected OpenRouter models |
| `ANTHROPIC_API_KEY` | -- | Anthropic: LLM dispatch for content-selector inference |
| `XAI_API_KEY` | -- | xAI/Grok: LLM dispatch for content-selector inference |
| `COHERE_API_KEY` | -- | Cohere: embedding + reranking |
| `WEB_CORE_LLM_MODEL` | auto-detect | Override the LLM model used for content-selector inference |
| `EMBEDDING_MODELS` | empty | Ordered CSV embedding model chain (`provider/model,...`); empty resolves Fastretrieval's local ONNX model manifest |
| `RERANK_MODELS` | empty | Ordered CSV rerank model chain (`provider/model,...`); empty resolves Fastretrieval's local ONNX cross-encoder manifest |
| `LLM_MODELS` | empty | Ordered CSV LLM model chain (`provider/model,...`); empty leaves optional LLM features disabled |
| `EMBEDDING_API_BASE` | -- | Custom embedding endpoint; managed Cohere gateway URL ends in `/cohere/v2/embed` |
| `RERANK_API_BASE` | -- | Custom rerank endpoint; managed Cohere gateway base ends in `/cohere` |
| `LLM_API_BASE` | -- | Provider-appropriate completion endpoint or CF AI Gateway base |
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
| `KAGI_API_KEY` | -- | Required for the `kagi` search backend |
| `FIRECRAWL_API_KEY` | -- | Optional for `firecrawl`; absent means a keyless attempt, not guaranteed free service |
| `GITHUB_TOKEN` | auto-detect | GitHub token for docs discovery |
| `SEARCH_BACKENDS` | `searxng` | Ordered CSV chain: `searxng`, `tavily`, `brave`, `exa`, `kagi`, `firecrawl`, `duckduckgo`, `startpage` |
| `WET_AUTO_SEARXNG` | `true` | Auto-start bundled SearXNG when the runtime includes its prerequisites; `uvx` plugin environments do not bundle them |
| `DISABLE_LOCAL_SEARCH` | `false` | Skip the embedded local SearXNG fallback while retaining external or cloud search backends |
| `BROWSER_BACKENDS` | empty -> `native` | Ordered CSV render chain: `native`, `browserless`, `cf-browser-rendering` |
| `SYNC_ENABLED` | `true` | Enable sync on eligible non-CF hosts; `DOCS_DB_BACKEND=cf-d1` disables it |
| `LOG_LEVEL` | `INFO` | Logging level |

### Backend Selection

- **Embedding, reranking, and LLM**: use the ordered `EMBEDDING_MODELS`, `RERANK_MODELS`, and `LLM_MODELS` chains; provider keys are inferred from each `provider/model` prefix.
- **Local model overrides**: use `LOCAL_EMBEDDING_MODEL` / `LOCAL_RERANK_MODEL`; built-in IDs resolve through Fastretrieval's model manifest, while custom embedding IDs require the matching local metadata variables above.
- **Legacy aliases**: `EMBEDDING_BACKEND`, `EMBEDDING_MODEL`, `RERANK_BACKEND`, and `RERANK_MODEL` are deprecated and honored for one release; migrate to the plural model chains.
- **Browser rendering**: `BROWSER_BACKENDS` escalates extraction renderers in listed order; an empty chain uses the local `native` browser. It does not select the browser used by `extract(action="interact")`.
- **Search**: `SEARCH_BACKENDS` tries providers in order on error or empty results. Hosted requests read the current subject's explicit chain and keys from the relay vault; only single-user stdio uses process settings. `duckduckgo` and `startpage` are credential-free and `uvx`-safe; keyed providers and an external `SEARXNG_URL` also work. Embedded SearXNG requires a suitable local/source-built runtime.
