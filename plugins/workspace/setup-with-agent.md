# Workspace MCP -- Agent Setup Guide

> Give this file to your AI agent to set up better-workspace-mcp.

Google Workspace over MCP: 11 composite tools (`docs`, `drive`, `calendar`, `gmail`, `sheets`, `slides`, `tasks`, `chat`, `people`, `forms`, `time`) plus `config` and `help`. Choose artifacts from the [published releases](https://github.com/n24q02m/workspace/releases); replace `<version>` in Docker examples with a published image version. HTTP examples configure your own endpoint; there is no endpoint hosted by the author.

## Prerequisite: a Google OAuth client

The user must create this themselves -- the server ships no Google client, so the consent screen and quota belong to the user's own project. This step cannot be automated by the agent.

1. Go to https://console.cloud.google.com/apis/credentials > Create credentials > OAuth client ID.
2. Type: **Desktop app** for stdio (Options 1 and 2), **Web application** for HTTP (Option 3). Google binds redirect URIs to the client type, so the two modes need two separate clients. Desktop consent returns to a loopback address.
3. Enable the Workspace APIs to be used (Docs, Drive, Calendar, Gmail, Sheets, Slides, Tasks, Chat, People, Forms) on the same project.
4. Add the user as a test user while the consent screen is unpublished.

Collect `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`.

## Method overview

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Single workstation. |
| **2. Fallback** | Docker stdio | stdio | `npx` PATH / Node version problems. |
| **3. Self-host** | Docker HTTP | HTTP | Multi-user, multi-device, team. |

> **Mutually exclusive -- pick ONE.** Installing via marketplace *and* adding a Docker/HTTP override loads both, because plugins match by endpoint (command string or URL), not by name. Options 2 and 3 also lose the plugin's hooks.

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

Restart Claude Code. On the **first run** the server opens the Google consent screen; the user approves once and the refresh token is stored encrypted locally (`~/.better-workspace/config.json`).

Equivalent manual config for any MCP client (Node >= 24.21.0):

```json
{
  "mcpServers": {
    "workspace": {
      "command": "npx",
      "args": ["--yes", "@n24q02m/workspace@latest"],
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

Published images default to HTTP (the last Dockerfile stage) and there is no `:stdio` tag, so override the transport:

```json
{
  "mcpServers": {
    "workspace": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MCP_TRANSPORT=stdio",
        "-e", "GOOGLE_OAUTH_CLIENT_ID",
        "-e", "GOOGLE_OAUTH_CLIENT_SECRET",
        "-v", "<your-home>/.better-workspace:/home/node/.better-workspace",
        "n24q02m/workspace:<version>"
      ]
    }
  }
}
```

A container cannot complete the first-run consent (the browser is on the host, the consent server inside the container). Authorize once outside Docker via Option 1, then mount `~/.better-workspace` as above, or use Option 3.

## Option 3: Docker HTTP (self-host)

Use the **Web application** client and a persistent `CREDENTIAL_SECRET`:

```bash
docker run -p 127.0.0.1:8087:8080 \
  -e HOST=0.0.0.0 \
  -e GOOGLE_OAUTH_CLIENT_ID=<your-web-client-id>.apps.googleusercontent.com \
  -e GOOGLE_OAUTH_CLIENT_SECRET=<your-web-client-secret> \
  -e CREDENTIAL_SECRET=<persistent-generated-secret> \
  -e WORKSPACE_USERS_FILE=/etc/workspace/users.toml \
  -v <your-users-file>:/etc/workspace/users.toml:ro \
  -v workspace-data:/home/node/.better-workspace \
  n24q02m/workspace:<version>
```

The server repository also ships `docker-compose.yml` plus the overlay `docker-compose.http.yml`, which reads the Web client as `GOOGLE_OAUTH_WEB_CLIENT_ID` / `GOOGLE_OAUTH_WEB_CLIENT_SECRET` and publishes on host loopback only (`127.0.0.1:8087`).

Each request must carry a bearer token listed in the users file (it maps each token to a user namespace; credentials are stored per namespace). Preserve `CREDENTIAL_SECRET` across restarts; HTTP startup fails without it. To expose the server beyond the host, put your own TLS reverse proxy in front.

Consent is not served over HTTP. For each user, run on the server host:

```bash
workspace auth --user <namespace>
```

### Claude Code (settings.json)

```json
{
  "mcpServers": {
    "workspace": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

### Codex CLI (config.toml)

```toml
[mcp_servers.workspace]
type = "http"
url = "https://<your-host>/mcp"
```

The Codex block omits the bearer header; how to set it differs per client.

### OpenCode (opencode.json)

```json
{
  "mcpServers": {
    "workspace": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

## Environment variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | -- | Desktop app client for stdio, Web application client for HTTP. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | -- | Secret of the same client. |
| `MCP_TRANSPORT` | No | `stdio` | `http` selects HTTP mode (`--http` / `TRANSPORT_MODE=http` equivalent). |
| `CREDENTIAL_SECRET` | Yes (http) | -- | Persistent secret deriving per-user credential-encryption keys. Required at HTTP startup. |
| `WORKSPACE_USERS_FILE` | Yes (http) | hull default location | Users file mapping each bearer token to a user namespace. |
| `PORT` | No | `0` (OS-assigned); `8080` in the image | Listen port (http). |
| `HOST` | No | `127.0.0.1` | Bind address (http); `0.0.0.0` to expose the container. |

## Multi-account

Every domain tool takes `account="<email>"`; omit it to use the primary. Manage accounts with `config`: `account_add`, `account_list`, `account_remove`, `account_set_default`. The first account authorized becomes primary; adding another never silently changes that. Naming an unconfigured account is an error, not a fallback to primary.

`account_add` chooses its flow by transport: in stdio it returns a loopback consent URL to open; over HTTP it returns the `workspace auth --user <namespace>` command to run on the host.

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
