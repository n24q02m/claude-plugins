# Imagine MCP -- Manual Setup Guide

> **2026-05-02 Update**: Plugin install (Method 1) now uses pure stdio mode with provider API key env vars.
> The previous "Zero-Config Relay" auto-spawn pattern has been removed.
> If you relied on the relay form to enter your keys, please:
> 1. Set at least one of `GEMINI_API_KEY` / `OPENAI_API_KEY` / `XAI_API_KEY` directly in plugin config (Method 1), OR
> 2. Switch to HTTP mode (Method 3 self-host) for browser-based paste-token setup.

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

- **Python** >= 3.13 (only if running from source; uvx and Docker bundle their own runtime)
- **At least one provider API key** -- Gemini, OpenAI, or xAI:
  - **Google AI Studio** (Gemini): https://aistudio.google.com/apikey
  - **OpenAI**: https://platform.openai.com/api-keys
  - **xAI** (Grok): https://console.x.ai

You can mix any subset. The server runs in degraded mode: providers without a key surface `CredentialMissingError` only when called.

## Method 1: Claude Code Plugin (Recommended)

Plugin marketplace install runs the server in **pure stdio mode** with provider env vars. No daemon-bridge, no auto-spawn, no relay form.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `XAI_API_KEY` | Optional | https://console.x.ai/ (default provider per spec) |
| `GEMINI_API_KEY` | Optional | https://aistudio.google.com/apikey |
| `OPENAI_API_KEY` | Optional | https://platform.openai.com/api-keys |

### Steps

1. Get at least one provider API key (see Prerequisites above).
2. Open Claude Code in your terminal.
3. Install the plugin (Claude Code prompts for `XAI_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` -- press Enter to skip the ones you do not have):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install imagine-mcp@n24q02m-plugins
   ```
4. Restart Claude Code -- the plugin auto-loads with your keys injected.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Method 2 (Docker stdio) or Method 3 (HTTP) below, DO NOT `/plugin install` this plugin — pick Method 2 or Method 3 instead. All three methods are mutually exclusive (see Method overview).

## Method 2: Docker stdio (fallback)

> **⚠️ Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall imagine-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Method 1 instead if you want full plugin features.

```json
{
  "mcpServers": {
    "imagine": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GEMINI_API_KEY",
        "-e", "OPENAI_API_KEY",
        "-e", "XAI_API_KEY",
        "ghcr.io/n24q02m/imagine-mcp:latest"
      ]
    }
  }
}
```

Set the keys you have in your shell profile:
```bash
export GEMINI_API_KEY="AIza..."
export OPENAI_API_KEY="sk-..."
export XAI_API_KEY="xai-..."
```

## Why upgrade to HTTP mode?

Stdio is the default and works fine for single-user local setups. You may want to switch to HTTP mode (Method 3 self-host) when you need any of the following:

- **claude.ai web compatibility** -- claude.ai (the web UI) supports HTTP MCP servers but cannot spawn local stdio processes.
- **One server shared across N Claude Code sessions** -- a single HTTP instance serves multiple terminals/IDEs without re-spawning per session.
- **Browser-based paste-token setup** -- enter API keys in a relay form rather than editing JSON config; keys saved encrypted on disk per JWT subject.
- **Multi-device credential sync** -- save keys once on your laptop, the same self-hosted server serves your desktop / tablet without re-entering.
- **Multi-user team sharing** -- a self-hosted server can serve multiple users, each with their own isolated set of provider keys (per-JWT-sub).
- **Always-on persistent process for webhooks/agents** -- HTTP servers stay alive between sessions, enabling background work, scheduled agents, or webhook listeners.

## Method 3: Docker HTTP (recommended)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall imagine-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `imagine-mcp:image-describe` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1 / Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### 3.1. Hosted (n24q02m.com)

Imagine MCP does **not** offer an n24q02m-hosted public instance -- provider API keys (Gemini / OpenAI / xAI) are paid per-token and would be billed to whoever runs the server. Use Method 3 (self-host) below to run your own HTTP instance, or stay on stdio for local single-user usage.

### 3.2. Self-host with docker-compose

Host your own multi-user paste-token server. Always multi-user (per-JWT-sub credential isolation). Each user pastes their own provider API keys via a browser form; keys are encrypted to disk and only decrypted for that user's JWT subject.

### Prerequisites

1. A public domain or tunnel pointing at your server (e.g. `https://imagine.your-domain.com`).
2. A DCR HMAC secret -- generate with `openssl rand -hex 32`.

### Required Env

| Variable | Description |
|:---------|:------------|
| `TRANSPORT_MODE=http` | Selects HTTP transport (multi-user). Equivalent: `MCP_TRANSPORT=http` or `--http` flag. |
| `PUBLIC_URL` | Public URL of your server (e.g. `https://imagine.your-domain.com`). Required to bind publicly. |
| `MCP_DCR_SERVER_SECRET` | HMAC secret for stateless Dynamic Client Registration. Generate via `openssl rand -hex 32`. |

Provider API keys (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `XAI_API_KEY`) are **not** server env vars in HTTP mode -- each user pastes their own keys via the relay form on first connect.

### Run the Server

```bash
docker run -p 8080:8080 \
  -e TRANSPORT_MODE=http \
  -e PUBLIC_URL=https://imagine.your-domain.com \
  -e MCP_DCR_SERVER_SECRET=$(openssl rand -hex 32) \
  ghcr.io/n24q02m/imagine-mcp:latest
```

Point clients to your server:
```json
{
  "mcpServers": {
    "imagine": {
      "type": "http",
      "url": "https://imagine.your-domain.com/mcp"
    }
  }
}
```

On first connect, the client opens a browser to your relay form. Each user pastes the API keys they want available (any subset of Gemini / OpenAI / xAI), submits, and the keys are stored encrypted under that user's JWT subject. Subsequent connections from the same user reuse the saved keys.

### Edge auth: relay password

Public HTTP deployments expose `<your-domain>/authorize` to URL discovery. To prevent random Internet users from accessing the relay form, mint a relay password:

```bash
openssl rand -hex 32
# Save in your skret / .env as:
MCP_RELAY_PASSWORD=<generated-32-byte-hex>
```

Share this password out-of-band (Signal/email/SMS) with anyone you invite to use your server. They will see a login form when first opening `/authorize`; once logged in, the cookie persists 24 hours.

**Single-user dev exception**: If `PUBLIC_URL=http://localhost:8080`, you can leave `MCP_RELAY_PASSWORD` empty to disable the gate. The server logs a warning if you skip the password with a non-localhost `PUBLIC_URL`.

## Test

Once configured, call from your MCP client:

```
understand(
  media_urls=["https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/300px-Cat_November_2010-1a.jpg"],
  prompt="What animal is this?",
  provider="gemini",
  tier="poor"
)
```

Expected: `{"text": "This is a cat...", "model": "gemini-3.1-flash-lite-preview", ...}`

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GEMINI_API_KEY` | At least one | -- | Google AI Studio (Gemini) API key. Stdio mode requires >=1 of the 3 provider keys. |
| `OPENAI_API_KEY` | At least one | -- | OpenAI API key (GPT-5.4 understanding + gpt-image generation). |
| `XAI_API_KEY` | At least one | -- | xAI (Grok) API key (Grok 4.20 understanding + Aurora generation). |
| `TRANSPORT_MODE` | No | `stdio` | Set to `http` for HTTP transport (multi-user paste-token). |
| `MCP_TRANSPORT` | No | -- | Equivalent to `TRANSPORT_MODE` (alias for parity). |
| `PUBLIC_URL` | Yes (http) | -- | Server's public URL for HTTP self-host. |
| `MCP_DCR_SERVER_SECRET` | Yes (http) | -- | HMAC secret for stateless Dynamic Client Registration. |

## Troubleshooting

### "No provider API keys set" / server exits immediately (stdio)

Stdio mode requires at least one of `GEMINI_API_KEY` / `OPENAI_API_KEY` / `XAI_API_KEY`. Set one in the plugin `env` block, or switch to HTTP mode (Method 3 self-host) for browser-based setup.

### `CredentialMissingError` on a specific provider call

You called `understand` / `generate` with a provider whose API key is not set. Either set that provider's key, or pass a different `provider=` argument (e.g. `provider="gemini"` if only Gemini key is set).

### `ProviderUnsupportedError` on video understanding / generation

OpenAI does not support video understanding or generation. xAI does not support video understanding. Use `provider="gemini"` for video paths -- see the capability matrix in [CLAUDE.md](../CLAUDE.md).

### Rate limit / quota errors

Try a different `provider=` argument, or wait and retry. Free Gemini tier is the most permissive for prototyping.

### uvx: old version or "command not found"

- Verify `uv` is installed: `uv --version`.
- Force latest: `uvx imagine-mcp@latest`.
- Clear the uv tool cache: `uv tool uninstall imagine-mcp && uvx imagine-mcp`.

### HTTP self-host: OAuth/relay form does not load

- Verify `PUBLIC_URL` matches the URL clients connect to.
- Verify `MCP_DCR_SERVER_SECRET` is set (server refuses to bind publicly without it).
- Check container logs for the relay setup URL on first request.
