# Notion MCP -- Manual Setup Guide

> The Notion server authenticates with a **Notion integration token** (`ntn_...`). There is no browser setup form and no OAuth flow: the token comes from the `NOTION_TOKEN` environment variable or from `notion auth`, which stores it under `~/.better-notion/`.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Quick local start, single workstation, no HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native `npx` hits PATH or Node version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, team self-host, claude.ai web compatibility. |

There is no endpoint hosted by the author. For HTTP you run the server yourself and put your own TLS reverse proxy in front of it.

> **Warning -- mutually exclusive, pick ONE per plugin**: If you choose Method 2 (Docker stdio override) or Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in the `/mcp` dialog (the plugin's stdio plus your override). Plugin matching is by **endpoint** (URL or command string), not by name -- and `npx` is not `docker` is not an HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills and hooks. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Prerequisites

- **Node.js** >= 24.21.0 (Method 1) or Docker (Methods 2 and 3)
- A **Notion account** with access to create integrations

## Method 1: Claude Code Plugin (Recommended)

Plugin marketplace install runs the server in **stdio mode** with the `NOTION_TOKEN` env var. There is no daemon bridge and no setup form.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig`). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `NOTION_TOKEN` | Required | https://www.notion.so/my-integrations (starts with `ntn_`) |

### Steps

1. Create a Notion integration token:
   - Go to https://www.notion.so/my-integrations
   - Click "New integration", name it (e.g. "Notion MCP"), select your workspace
   - Copy the "Internal Integration Secret" (starts with `ntn_`)
   - **Share pages with the integration**: open a Notion page > "..." > Connections > select your integration. Repeat for each page or database you want accessible.
2. Open Claude Code in your terminal
3. Install the plugin (Claude Code prompts for `NOTION_TOKEN` -- paste the secret you copied above):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-notion-mcp@n24q02m-plugins
   ```
4. Restart Claude Code. The plugin auto-loads with your token injected via `${user_config.NOTION_TOKEN}`.

> **Note**: This installs the full plugin (skills + hooks + stdio MCP server). If you would rather use Method 2 (Docker stdio) or Method 3 (HTTP) below, do NOT `/plugin install` this plugin -- pick Method 2 or Method 3 instead. All three methods are mutually exclusive (see Method overview).

Or configure it by hand in any MCP client:

```jsonc
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["--yes", "@n24q02m/notion@latest"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "NOTION_TOKEN": "<your-notion-token>"
      }
    }
  }
}
```

### Store the token with `notion auth` instead

If you would rather not keep the token in client config, store it once on the machine that runs the server:

```bash
NOTION_TOKEN=<your-notion-token> npx -y @n24q02m/notion auth
```

`notion auth` reads the token from `NOTION_TOKEN` or prompts for it (it is never taken from command-line arguments), checks it against Notion, and saves it to `~/.better-notion/config.json` with owner-only file permissions. Later runs pick it up without `NOTION_TOKEN` being set. If neither is present in stdio mode, the server exits with an error on stderr listing both options.

## Method 2: Docker stdio (fallback)

> **Warning -- before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-notion-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (the plugin's `npx` stdio and your `docker run` stdio) load simultaneously, since plugins match by endpoint (command string), not by name.
>
> **Trade-off accepted**: choosing this method means you lose this plugin's skills and hooks. Use Method 1 instead if you want full plugin features.

1. Pull the image:
   ```bash
   docker pull n24q02m/notion:latest
   ```

2. Add to your MCP client config:
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

3. Set `NOTION_TOKEN` in your shell profile:
   ```bash
   export NOTION_TOKEN="ntn_..."
   ```

The image is also published as `ghcr.io/n24q02m/notion` (multi-arch: amd64 and arm64).

## Why use HTTP mode?

Stdio is the default and works fine for single-user local setups. Consider a self-hosted HTTP instance (Method 3) when you need any of the following:

- **claude.ai web compatibility** -- claude.ai (the web UI) supports HTTP MCP servers but cannot spawn local stdio processes.
- **One server shared across N Claude Code sessions** -- a single HTTP instance serves multiple terminals and IDEs without re-spawning per session.
- **Multi-device access** -- the Notion token stays on the server host; each device only needs the server URL and its own bearer token.
- **Multi-user team sharing** -- in `multi` mode each user has their own bearer token and their own Notion token namespace.
- **Always-on persistent process** -- an HTTP server stays alive between sessions.

## Method 3: Docker HTTP (self-host)

> **Warning -- before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-notion-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (the plugin's stdio and your HTTP override) load simultaneously, since plugins match by endpoint, not name.
>
> **Trade-off accepted**: choosing this method means you lose this plugin's skills and hooks. For example, the `organize-database` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: the `userConfig` prompt only configures `NOTION_TOKEN` for stdio mode (Method 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- a separate path from `userConfig`, not driven by the install prompt.

HTTP mode is turned on with `--http`, `MCP_TRANSPORT=http`, or `TRANSPORT_MODE=http`. Clients authenticate to the server with a **bearer token**; the server talks to Notion with an integration token stored on the host. Choose how clients authenticate with `MCP_AUTH_MODE`:

| `MCP_AUTH_MODE` | Behavior |
|---|---|
| `multi` (default) | Each user is listed in the users file (`MCP_USERS_FILE`, default `~/.hull/users.toml`) and gets their own bearer token and Notion token namespace. Store a user's Notion token with `notion auth --user <namespace>` on the server host. |
| `token` | Every client shares one bearer token. Set `MCP_AUTH_TOKEN_HASH` to its `scrypt$...` hash, minted with the `token hash` subcommand. `MCP_RPM` optionally caps requests per minute. The Notion token is the default one (`NOTION_TOKEN` or `notion auth`). |
| `no-auth` | No bearer check. Use only on a trusted local network or loopback. |

### Run the server

Shared-token example:

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

Or use the compose file shipped in the server repo, which publishes the server on the host loopback interface only (`127.0.0.1:8081`):

```bash
export MCP_AUTH_MODE=token
export MCP_AUTH_TOKEN_HASH='scrypt$...'
docker compose -f docker-compose.http.yml up
```

The server then listens on `http://localhost:8081/mcp`. To expose it beyond the host, put your own TLS reverse proxy in front of the loopback port.

Point clients at the host you deployed it on:

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

In `token` and `multi` modes the client must send `Authorization: Bearer <your-token>`. How to set that header differs per client (the Codex CLI block above omits it); see your client's documentation for passing a header or bearer token.

## Credential Setup

1. Go to https://www.notion.so/my-integrations
2. Create a new integration for your workspace
3. Copy the "Internal Integration Secret" (`ntn_...`)
4. Share each page or database with the integration via the Connections menu
5. Provide the token as `NOTION_TOKEN` (plugin field or environment variable), or store it with `notion auth` (or `notion auth --user <namespace>` for a user in HTTP `multi` mode)

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `NOTION_TOKEN` | Yes (stdio, unless stored with `notion auth`) | -- | Notion internal integration token (`ntn_...`). In HTTP mode it applies to the default namespace only. |
| `MCP_TRANSPORT` / `TRANSPORT_MODE` | No | `stdio` | Set either to `http` to enable HTTP transport (`--http` on the command line does the same). |
| `MCP_AUTH_MODE` | No (http) | `multi` | `multi`, `token`, or `no-auth`. |
| `MCP_USERS_FILE` | No (http, `multi`) | `~/.hull/users.toml` | Users file for `multi` mode. |
| `MCP_AUTH_TOKEN_HASH` | Yes (http, `token`) | -- | `scrypt$...` hash of the shared bearer token. |
| `MCP_RPM` | No (http, `token`) | -- | Optional per-minute request cap. |
| `PORT` | No | `0` (OS-assigned) | Server port; set explicitly to bind a fixed port. |
| `HOST` | No | `127.0.0.1` | Bind address (http mode); set `0.0.0.0` to expose the container. |

## Troubleshooting

### "Could not find integration" or 401 Unauthorized

- Verify your `NOTION_TOKEN` starts with `ntn_` and is a valid Internal Integration Secret.
- Ensure the integration has not been deleted or revoked at https://www.notion.so/my-integrations.
- In HTTP mode a 401 on the MCP endpoint itself means the bearer token is missing or wrong; a Notion 401 inside a tool result means the stored Notion token is bad.

### Tool returns empty results

- The integration can only access pages explicitly shared with it. Click "..." on a Notion page > Connections > add your integration.
- Child pages inherit the parent's connections, but databases must be shared individually.

### Tool says to run `notion auth`

- No Notion token is available to the server for your user. Set `NOTION_TOKEN`, or run `notion auth` (or `notion auth --user <namespace>` in HTTP `multi` mode) on the machine that runs the server. Check with `config(action="status")`.

### npx: old version or "command not found"

- Verify Node.js >= 24.21.0: `node --version`.
- Clear the npx cache or use the `@latest` tag: `npx -y @n24q02m/notion@latest`.

See the [troubleshooting guide](/servers/notion/troubleshooting/) for more.
