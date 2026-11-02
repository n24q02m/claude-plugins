# Notion MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up better-notion-mcp.

The server authenticates with a **Notion integration token** (`ntn_...`). There is no browser setup form and no OAuth flow. The token comes from the `NOTION_TOKEN` environment variable or from `notion auth`, which stores it under `~/.better-notion/`. The user must create the integration themselves; the agent cannot do that step.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Quick local start, single workstation. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native `npx` hits PATH or Node version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, team self-host, claude.ai web compatibility. |

There is no endpoint hosted by the author; HTTP examples configure your own deployment.

> **Warning -- mutually exclusive, pick ONE per plugin**: If you choose Method 2 (Docker stdio override) or Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in the `/mcp` dialog, because plugins match by **endpoint** (URL or command string), not by name. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills and hooks. For full plugin features, use Option 1.

## Option 1: Claude Code Plugin (Recommended)

Plugin marketplace install runs the server in **stdio mode** with the `NOTION_TOKEN` env var.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts for the following credentials (declared in `userConfig`). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `NOTION_TOKEN` | Required | https://www.notion.so/my-integrations (starts with `ntn_`) |

### Steps

1. Create a Notion integration token (user step):
   - Go to https://www.notion.so/my-integrations
   - Click "New integration", name it, select your workspace
   - Copy the "Internal Integration Secret" (starts with `ntn_`)
   - Share pages/databases with the integration: open page > "..." > Connections > select your integration
2. Install the plugin (Claude Code prompts for `NOTION_TOKEN`):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-notion-mcp@n24q02m-plugins
   ```
3. Restart Claude Code -- the plugin auto-loads with your token.

This installs the server with skills: `/organize-database`, `/bulk-update`.

> **Note**: This installs the full plugin (skills + hooks + stdio MCP server). If you would rather use Option 2 (Docker stdio) or Option 3 (HTTP) below, do NOT `/plugin install` this plugin. All three methods are mutually exclusive (see Method overview).

To keep the token out of client config, store it once on the machine that runs the server instead:

```bash
NOTION_TOKEN=<your-notion-token> npx -y @n24q02m/notion auth
```

`notion auth` reads the token from `NOTION_TOKEN` or prompts for it (never from argv), verifies it with Notion, and saves it to `~/.better-notion/config.json`.

## Option 2: Docker stdio (fallback)

> **Warning -- before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-notion-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries load simultaneously since plugins match by endpoint (command string), not by name.
>
> **Trade-off accepted**: choosing this method means you lose this plugin's skills and hooks. Use Option 1 if you want full plugin features.

```json
{
  "mcpServers": {
    "notion": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MCP_TRANSPORT=stdio",
        "-e", "NOTION_TOKEN",
        "n24q02m/notion:latest"
      ]
    }
  }
}
```

Set `NOTION_TOKEN` in your shell profile or pass it inline.

## Option 3: Docker HTTP (self-host)

> **Warning -- before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-notion-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries load simultaneously since plugins match by endpoint, not name.
>
> **Trade-off accepted**: choosing this method means you lose this plugin's skills and hooks. For example, the `organize-database` skill will no longer be available. Use Option 1 if you want full plugin features.

> **Switching transport vs. setting credentials**: the `userConfig` prompt only configures `NOTION_TOKEN` for stdio mode (Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- a separate path from `userConfig`, not driven by the install prompt.

Stdio is enough for single-user local setups. Choose HTTP for claude.ai web compatibility, one server shared across many sessions, multi-device access, or a team where each user has their own bearer token.

HTTP is enabled with `--http`, `MCP_TRANSPORT=http`, or `TRANSPORT_MODE=http`. Clients authenticate with a bearer token, chosen by `MCP_AUTH_MODE`:

- `multi` (default): each user is listed in `MCP_USERS_FILE` (default `~/.hull/users.toml`) and gets their own Notion token namespace; store it with `notion auth --user <namespace>` on the server host.
- `token`: one shared bearer token; set `MCP_AUTH_TOKEN_HASH` to its `scrypt$...` hash (mint it with the `token hash` subcommand).
- `no-auth`: no bearer check; trusted local use only.

```bash
docker run -p 8080:8080 \
  -e TRANSPORT_MODE=http \
  -e PORT=8080 \
  -e HOST=0.0.0.0 \
  -e MCP_AUTH_MODE=token \
  -e MCP_AUTH_TOKEN_HASH='scrypt$...' \
  -e NOTION_TOKEN \
  n24q02m/notion:latest
```

The compose file `docker-compose.http.yml` in the server repo publishes the same server on host loopback only (`http://localhost:8081/mcp`); put your own TLS reverse proxy in front to expose it.

Client config:

**Claude Code** -- `.claude/settings.json` or `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "notion": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

**Codex CLI** -- `~/.codex/config.toml`:
```toml
[mcp_servers.notion]
type = "http"
url = "https://<your-host>/mcp"
```

**OpenCode** -- `opencode.json`:
```json
{
  "mcpServers": {
    "notion": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

The client must send `Authorization: Bearer <your-token>` in `token` and `multi` modes; how to set that header differs per client (the Codex CLI block above omits it).

## Environment Variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `NOTION_TOKEN` | Yes (stdio, unless stored with `notion auth`) | -- | Notion internal integration token (`ntn_...`). In HTTP mode it applies to the default namespace only. |
| `MCP_TRANSPORT` / `TRANSPORT_MODE` | No | `stdio` | Set either to `http` to enable HTTP transport. |
| `MCP_AUTH_MODE` | No (http) | `multi` | `multi`, `token`, or `no-auth`. |
| `MCP_USERS_FILE` | No (http, `multi`) | `~/.hull/users.toml` | Users file for `multi` mode. |
| `MCP_AUTH_TOKEN_HASH` | Yes (http, `token`) | -- | `scrypt$...` hash of the shared bearer token. |
| `MCP_RPM` | No (http, `token`) | -- | Optional per-minute request cap. |
| `PORT` | No | `0` (OS-assigned) | Server port (http mode). |
| `HOST` | No | `127.0.0.1` | Bind address (http mode); set `0.0.0.0` to expose the container. |

## Authentication

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it and select the workspace
4. Copy the "Internal Integration Secret" (starts with `ntn_`)
5. Share pages/databases with the integration (click "..." on a page > Connections > select your integration)
6. Provide the token as `NOTION_TOKEN`, or store it with `notion auth` (`notion auth --user <namespace>` for an HTTP `multi` user)

## Verification

After setup, verify the server is working:

```
Use the workspace tool with action "info" to verify the server is connected to Notion.
```

Expected: workspace name, ID, and bot user information.

To check credentials without calling Notion:

```
Use the config tool with action "status".
```

Expected: `state` is `configured`, with `has_token` true and `token_source` of `environment` or `config`. If it says `awaiting_setup`, run `notion auth` on the server host.
