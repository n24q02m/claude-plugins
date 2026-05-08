# Imagine MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up imagine-mcp.

> **2026-05-02 Update (v<auto>+)**: Plugin install (Option 1) now uses pure stdio mode with provider API key env vars.
> The previous "Zero-Config Relay" auto-spawn pattern has been removed.
> If you relied on the relay form to enter your keys, please:
> 1. Set at least one of `GEMINI_API_KEY` / `OPENAI_API_KEY` / `XAI_API_KEY` directly in plugin config (Option 1), OR
> 2. Switch to HTTP mode (self-host) for browser-based paste-token setup -- see `setup-manual.md` "Method 3: Docker HTTP (recommended)".

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, no OAuth/HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx/npx hits PATH or Python version issues. |
| **3. Recommended** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, OAuth/relay-form auth, team self-host, claude.ai web compatibility. |

All MCP servers across this stack share this priority hierarchy. Note: 2 plugins (`better-godot-mcp` and `better-code-review-graph`) only support Method 1 (stdio) -- they need direct host access to project files / repo paths and don't ship Docker / HTTP variants.

> **⚠️ Mutually exclusive — pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name — and `npx`/`uvx` ≠ `docker` ≠ HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Option 1: Claude Code Plugin (Recommended)

Plugin marketplace install runs the server in **pure stdio mode** with provider env vars. No daemon-bridge, no auto-spawn, no relay form.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `XAI_API_KEY` | Optional | https://console.x.ai/ (default provider per spec) |
| `GEMINI_API_KEY` | Optional | https://aistudio.google.com/apikey |
| `OPENAI_API_KEY` | Optional | https://platform.openai.com/api-keys |

### Steps

1. Get at least one provider API key (see table above).
2. Install the plugin (press Enter to skip providers you do not have):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install imagine-mcp@n24q02m-plugins
   ```

This installs the server with skill: `/image-describe`.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Option 2 (Docker stdio) or Option 3 (HTTP) below, DO NOT `/plugin install` this plugin — pick Option 2 or Option 3 instead. All three methods are mutually exclusive (see Method overview).

## Option 2: Docker stdio (fallback)

> **⚠️ Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall imagine-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Option 1 instead if you want full plugin features.

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

Set the keys in your shell profile or pass them inline.

## Why upgrade to HTTP mode?

Stdio is the default and works fine for single-user local setups. You may want to switch to HTTP self-host mode when you need any of the following:

- **claude.ai web compatibility** -- claude.ai (the web UI) supports HTTP MCP servers but cannot spawn local stdio processes.
- **One server shared across N Claude Code sessions** -- a single HTTP instance serves multiple terminals/IDEs without re-spawning per session.
- **Browser-based paste-token setup** -- enter API keys in a relay form rather than editing JSON config; keys saved encrypted on disk per JWT subject.
- **Multi-device credential sync** -- save keys once, the same self-hosted server serves your desktop / tablet without re-entering.
- **Multi-user team sharing** -- a self-hosted server can serve multiple users, each with their own isolated set of provider keys (per-JWT-sub).
- **Always-on persistent process for webhooks/agents** -- HTTP servers stay alive between sessions, enabling background work, scheduled agents, or webhook listeners.

## Option 3: Docker HTTP (recommended)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall imagine-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `imagine-mcp:image-describe` skill will no longer be available. Use Option 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1 / Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### 3.2. Self-host with docker-compose

Imagine MCP does **not** offer an n24q02m-hosted public instance -- provider API keys are paid per-token. Run your own:

```bash
docker run -p 8080:8080 \
  -e TRANSPORT_MODE=http \
  -e PUBLIC_URL=https://imagine.your-domain.com \
  -e MCP_DCR_SERVER_SECRET=$(openssl rand -hex 32) \
  ghcr.io/n24q02m/imagine-mcp:latest
```

Then point clients at your server:

### Claude Code (settings.json)

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

### Codex CLI (config.toml)

```toml
[mcp_servers.imagine]
type = "http"
url = "https://imagine.your-domain.com/mcp"
```

### OpenCode (opencode.json)

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

On first use, a browser window opens to the relay form. Each user pastes the API keys they want (any subset of Gemini / OpenAI / xAI), submits, and the keys are stored encrypted under that user's JWT subject.

For full self-host setup details (TLS, tunnel, env reference), see [setup-manual.md](setup-manual.md) "Method 3 (Docker HTTP — Self-host)".

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

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GEMINI_API_KEY` | At least one (stdio) | -- | Google AI Studio (Gemini) API key. |
| `OPENAI_API_KEY` | At least one (stdio) | -- | OpenAI API key. |
| `XAI_API_KEY` | At least one (stdio) | -- | xAI (Grok) API key. |
| `TRANSPORT_MODE` | No | `stdio` | Set to `http` for multi-user paste-token mode. |
| `MCP_TRANSPORT` | No | -- | Equivalent to `TRANSPORT_MODE`. |
| `PUBLIC_URL` | Yes (http) | -- | Server's public URL for HTTP self-host. |
| `MCP_DCR_SERVER_SECRET` | Yes (http) | -- | HMAC secret for stateless client registration. |

## Authentication

### Stdio Mode (Provider API Keys)

Get at least one of:
- **Gemini**: https://aistudio.google.com/apikey -- key starts with `AIza`
- **OpenAI**: https://platform.openai.com/api-keys -- key starts with `sk-`
- **xAI**: https://console.x.ai -- key starts with `xai-`

Any subset is fine -- providers without a key surface `CredentialMissingError` only when called.

### HTTP Self-Host Mode (Paste-Token Relay)

No env-var keys on the server. Each user pastes their own provider API keys via the relay form on first connect; keys are encrypted to disk per JWT subject.

## Verification

After setup, verify the server is working:

```
Use the understand tool with a sample image URL and prompt to verify the server is connected and at least one provider key is configured.
```

Example call:
```
understand(
  media_urls=["https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/300px-Cat_November_2010-1a.jpg"],
  prompt="What animal is this?",
  provider="gemini",
  tier="poor"
)
```

Expected: a JSON dict with `text` describing a cat and `model` naming a Gemini model ID.
