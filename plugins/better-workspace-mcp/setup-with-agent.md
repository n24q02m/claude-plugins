# Better Workspace MCP -- Agent Setup Guide

> Give this file to your AI agent to set up better-workspace-mcp.

Google Workspace over MCP: 11 composite tools (`docs`, `drive`, `calendar`, `gmail`, `sheets`, `slides`, `tasks`, `chat`, `people`, `forms`, `time`) plus `config` and `help`. Currently beta — `0.1.0-beta.2` on npm, `:beta` on Docker Hub / GHCR. No hosted instance exists; HTTP mode is self-host only.

## Prerequisite: a Google OAuth client

The user must create this themselves — the server ships no Google client, so the consent screen and quota belong to the user's own project. This step cannot be automated by the agent.

1. Go to https://console.cloud.google.com/apis/credentials → Create credentials → OAuth client ID.
2. Type: **Desktop app** for stdio (Options 1 and 2), **Web application** for HTTP (Option 3). Desktop is correct for stdio because consent returns to a loopback address; a Web client is required for HTTP because consent returns to a fixed `/accounts/callback` that Google must know in advance.
3. Enable the Workspace APIs to be used (Docs, Drive, Calendar, Gmail, Sheets, Slides, Tasks, Chat, People, Forms) on the same project.
4. Add the user as a test user while the consent screen is unpublished.

Collect `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`.

## Method overview

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Single workstation. |
| **2. Fallback** | Docker stdio | stdio | `npx` PATH / Node version problems. |
| **3. Self-host** | Docker HTTP | HTTP | Multi-user, multi-device, team. |

> **Mutually exclusive — pick ONE.** Installing via marketplace *and* adding a Docker/HTTP override loads both, because plugins match by endpoint (command string or URL), not by name. Options 2 and 3 also lose the plugin's hooks.

## Option 1: Claude Code plugin (recommended -- stdio + userConfig prompt)

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-workspace-mcp@n24q02m-plugins
```

Claude Code prompts for both values (declared in `userConfig`; sensitive ones go to the system keychain):

| Field | Required |
|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | Required |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Required |

Restart Claude Code. On the **first run** the server opens the Google consent screen; the user approves once and the refresh token is stored encrypted locally.

Equivalent manual config for any MCP client:

```json
{
  "mcpServers": {
    "better-workspace-mcp": {
      "command": "npx",
      "args": ["--yes", "@n24q02m/better-workspace-mcp@latest"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "GOOGLE_OAUTH_CLIENT_ID": "<your-client-id>.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "<your-client-secret>"
      }
    }
  }
}
```

## Option 2: Docker stdio (fallback)

The published image defaults to HTTP (`MCP_TRANSPORT=http` baked in) and there is no `:stdio` tag, so override the transport:

```json
{
  "mcpServers": {
    "better-workspace-mcp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MCP_TRANSPORT=stdio",
        "-e", "GOOGLE_OAUTH_CLIENT_ID",
        "-e", "GOOGLE_OAUTH_CLIENT_SECRET",
        "n24q02m/better-workspace-mcp:beta"
      ]
    }
  }
}
```

A container has no browser for the first-run consent. Authorize once via Option 1, or use Option 3.

## Option 3: Docker HTTP (self-host)

```bash
docker run -p 8080:8080 \
  -e HOST=0.0.0.0 \
  -e PUBLIC_URL=https://<your-host> \
  -e GOOGLE_OAUTH_CLIENT_ID=<your-web-client-id>.apps.googleusercontent.com \
  -e GOOGLE_OAUTH_CLIENT_SECRET=<your-web-client-secret> \
  -e MCP_RELAY_PASSWORD=$(openssl rand -hex 32) \
  n24q02m/better-workspace-mcp:beta
```

Register `https://<your-host>/accounts/callback` as an authorized redirect URI on the Web client. Auth is OAuth 2.1 delegated to Google; each user's credentials are keyed by their JWT `sub`.

`MCP_RELAY_PASSWORD` gates `/authorize` — without it, anyone who discovers the URL can open a session on the deployment. Share it out-of-band. It is optional only when `PUBLIC_URL` is localhost.

### Claude Code (settings.json)

```json
{
  "mcpServers": {
    "better-workspace-mcp": { "type": "http", "url": "https://<your-host>/mcp" }
  }
}
```

### Codex CLI (config.toml)

```toml
[mcp_servers.better-workspace-mcp]
type = "http"
url = "https://<your-host>/mcp"
```

### OpenCode (opencode.json)

```json
{
  "mcpServers": {
    "better-workspace-mcp": { "type": "http", "url": "https://<your-host>/mcp" }
  }
}
```

## Environment variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | -- | Desktop app client for stdio, Web application client for HTTP. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | -- | Secret of the same client. |
| `MCP_TRANSPORT` | No | `stdio` | `http` selects HTTP mode (`--http` / `TRANSPORT_MODE=http` equivalent). |
| `PUBLIC_URL` | Yes (http) | -- | Public URL used to build OAuth redirects. |
| `MCP_RELAY_PASSWORD` | Yes (http, public) | -- | Gates `/authorize`. Optional only on localhost. |
| `CREDENTIAL_SECRET` | No (http) | auto-generated | Per-user credential store key; auto-generated to a 0600 file if unset. Set it to survive restarts. |
| `PORT` | No | `8080` in the image | Listen port (http). |
| `HOST` | No | -- | Bind address (http); `0.0.0.0` to expose the container. |
| `MCP_AUTH_DISABLE` | No (http) | -- | `1` skips Bearer JWT verification. Only behind an external auth gateway. |
| `MCP_NO_BROWSER` / `NO_BROWSER` | No | -- | Suppress the first-run browser launch. |

## Multi-account

Every domain tool takes `account="<email>"`; omit it to use the primary. Manage accounts with `config`: `account_add`, `account_list`, `account_remove`, `account_set_default`. The first account authorized becomes primary; adding another never silently changes that. Naming an unconfigured account is an error, not a fallback to primary.

In HTTP mode `account_add` completes through `/accounts/callback`.

## Verification

`time` needs no Google account, so it verifies wiring independently of consent:

```
Use the time tool with action "getCurrentTime".
```

Expected: the current local time.

Then:

```
Use the config tool with action "status".
```

Expected: `awaiting_setup` before the first consent, and the acting account's email afterwards.
