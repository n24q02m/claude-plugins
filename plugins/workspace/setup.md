# Workspace MCP -- Manual Setup Guide

> Choose a version from the [published releases](https://github.com/n24q02m/workspace/releases). The examples below configure your own HTTP endpoint; there is no endpoint hosted by the author. Replace `<version>` in Docker examples with a published image version.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Quick local start, single workstation, your own Google OAuth client. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native `npx` hits PATH or Node version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-user, multi-device, team deploy, claude.ai web compatibility. |

> **Warning -- mutually exclusive, pick ONE**: If you choose Method 2 or Method 3, do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in the `/mcp` dialog. Plugin matching is by **endpoint** (URL or command string), not by name -- and `npx` is not `docker` is not an HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's hooks. For full plugin features, use Method 1.

## Prerequisites

- **Node.js** >= 24.21.0 (Method 1) or Docker (Methods 2 and 3)
- A Google account, and a Google Cloud project where you can create an OAuth client

### Create the Google OAuth client

The server never ships a Google client of its own -- you bring your own, so the consent screen names your project and the quota is yours.

1. Open the [Google Cloud Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth client ID**. The type depends on the mode you plan to run, and Google binds redirect URIs to the client type, so the two modes cannot share one client:
   - **Desktop app** for stdio (Methods 1 and 2). Desktop is the right type because the server receives the consent redirect on a [loopback address](https://developers.google.com/identity/protocols/oauth2/native-app), not on a public URL.
   - **Web application** for HTTP (Method 3).
3. Enable the Workspace APIs you plan to call on the same project (Docs, Drive, Calendar, Gmail, Sheets, Slides, Tasks, Chat, People, Forms -- enable only what you need).
4. While the consent screen is unpublished, add yourself as a test user.

> A Desktop-app client secret is **not** a confidential secret in the OAuth sense -- installed apps cannot keep one. It still identifies your project, so keep it out of public repos.

## Method 1: Claude Code Plugin (recommended)

Plugin install runs in **stdio mode** with the OAuth client provided via the `userConfig` install prompt.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts for the following. Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | Required | Desktop app OAuth client, ends with `.apps.googleusercontent.com` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Required | Client secret of that same client |

### Steps

1. Create a Desktop app OAuth client (see "Create the Google OAuth client" above).
2. Open Claude Code in your terminal.
3. Install the plugin (Claude Code prompts for both values):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-workspace-mcp@n24q02m-plugins
   ```
4. Restart Claude Code -- the plugin auto-loads with your client injected.
5. On the **first run** the server opens the Google consent screen in your browser. Approve it once; the refresh token is stored encrypted on your machine (`~/.better-workspace/config.json`), so later runs start without asking again.

Or configure it by hand in any MCP client:

```jsonc
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

## Method 2: Docker stdio (fallback)

> **Warning -- before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-workspace-mcp@n24q02m-plugins` first if you previously ran `/plugin install`.

Published images are built from the last stage of the Dockerfile, which is the **HTTP** server (`MCP_TRANSPORT=http`, port 8080), and there is no separate `:stdio` tag. Stdio over Docker therefore means overriding the transport explicitly with `-e MCP_TRANSPORT=stdio`:

```bash
docker pull n24q02m/workspace:<version>
```

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

Set the values in your shell profile:

```bash
export GOOGLE_OAUTH_CLIENT_ID="<your-client-id>.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="<your-client-secret>"
```

First-run consent does not work from inside a container: the consent server listens on a loopback port inside the container while the browser runs on the host. Authorize once outside Docker (Method 1, or `npx @n24q02m/workspace`), then bind-mount the resulting `~/.better-workspace` directory as shown above so the container reuses the stored token.

The corresponding GHCR image is `ghcr.io/n24q02m/workspace:<version>`; select the version from the release's published assets.

## Why upgrade to HTTP mode?

Stdio mode is the default and works for single-user local development. Consider HTTP when you need any of:

- **Multi-user / team sharing** -- each user is mapped by a bearer token to a namespace, and each namespace keeps its Google credentials in its own bucket, so one deployment serves several people without them sharing an account
- **claude.ai web compatibility** -- connect the server directly from claude.ai without a local CLI
- **1 server shared across N Claude Code sessions** -- no per-session process proliferation
- **Multi-device access** -- credentials persist server-side; new devices just point at the URL with their bearer token

## Method 3: Docker HTTP (self-host)

> **Warning -- before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-workspace-mcp@n24q02m-plugins` first if you previously ran `/plugin install`.

> **Switching transport vs. setting credentials**: the `userConfig` prompt only configures the OAuth client for stdio mode (Method 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- a separate path from `userConfig`, not driven by the install prompt.

HTTP mode needs a **Web application** OAuth client (a Desktop client will not work), a persistent `CREDENTIAL_SECRET`, and a users file that maps each bearer token to a user namespace. Create the Web client in the Cloud Console and keep it separate from the Desktop client used for stdio.

Run your own HTTP service:

```bash
# HOST=0.0.0.0 binds all interfaces so the host can reach the container.
# PORT is already 8080 in the image; set it if you want a different one.
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

Or use the compose overlay from the server repository, which publishes the server on host loopback only (`127.0.0.1:8087`):

```bash
docker compose -f docker-compose.yml -f docker-compose.http.yml up
```

The overlay reads the Web client as `GOOGLE_OAUTH_WEB_CLIENT_ID` / `GOOGLE_OAUTH_WEB_CLIENT_SECRET` (renamed to `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` inside the container so an HTTP deploy never overwrites the Desktop credentials that stdio installs use), plus `CREDENTIAL_SECRET` and `WORKSPACE_USERS_FILE`, from your shell or an `.env` file.

Keep `CREDENTIAL_SECRET` stable across restarts: it derives each user's credential-encryption key, and the server refuses to start without it. The users file maps each bearer token to a user namespace (hull `multi` auth); leave `WORKSPACE_USERS_FILE` unset to use the default location.

To expose the server beyond the local machine, put your own TLS reverse proxy on the same host in front of the loopback port.

### Add a Google account for a user

Consent is not served over HTTP. For each user, run on the server host:

```bash
workspace auth --user <namespace>
```

This runs the Google consent flow and stores the account under that namespace. `config(action="account_add")` over HTTP returns the same command for you to run.

### Client config

Point your MCP client at the host you deployed it on, sending the user's bearer token:

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

How the bearer header is set differs per client; see your client's documentation.

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | -- | OAuth client ID. Desktop app type for stdio, Web application type for HTTP. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | -- | Client secret of the same OAuth client. |
| `MCP_TRANSPORT` | No | `stdio` | `http` selects HTTP mode. `--http` on the command line and `TRANSPORT_MODE=http` do the same. |
| `CREDENTIAL_SECRET` | Yes (http) | -- | Persistent secret deriving each user's credential-encryption key. HTTP startup fails if it is absent. |
| `WORKSPACE_USERS_FILE` | Yes (http) | hull default location | Users file that maps each bearer token to a user namespace. |
| `PORT` | No | `0` (OS-assigned); `8080` in the image | Listen port (http mode). |
| `HOST` | No | `127.0.0.1` | Bind address (http mode); set `0.0.0.0` to expose the container. |

Credentials are stored under `~/.better-workspace/` (the data volume in the container). A legacy `~/.better-workspace-mcp/` directory is read as a fallback.

## Verification

After setup, check that the server answers at all -- `time` needs no Google account:

```
Use the time tool with action "getCurrentTime".
```

Then confirm the credentials landed:

```
Use the config tool with action "status".
```

Before the first consent this reports `awaiting_setup`; afterwards it names the account the server is acting as.

## Multi-account

Every domain tool takes an `account` parameter -- the email of the Google account the call acts as. Omit it and the call runs against the primary account. Accounts are managed through `config`: `account_add`, `account_list`, `account_remove`, `account_set_default`. See the [tools reference](/servers/workspace/tools/).

`account_add` picks its flow by transport. In stdio it starts a temporary loopback consent server and returns the URL to open (valid for a short time). In HTTP mode it returns the `workspace auth --user <namespace>` command to run on the host.

## Troubleshooting

### "Access blocked: This app is not verified"

Your consent screen is still unpublished. Add your Google account as a test user in the Cloud Console, or publish the consent screen.

### `redirect_uri_mismatch`

Google binds redirect URIs to the OAuth client type. Stdio needs a Desktop app client; HTTP needs a Web application client, and a Desktop client will fail there. If the type is right, check that the Web client's authorized redirect URIs match what the consent flow uses, scheme and path exactly.

### The browser never opens on first run

Containers and headless hosts have no browser. Authorize once via Method 1 on a workstation and mount the resulting `~/.better-workspace` directory into the container, or run HTTP mode and consent with `workspace auth --user <namespace>` on the host.

### A Workspace API returns 403

The API is probably not enabled on your Cloud project. Enable it under APIs & Services > Library, then retry -- the scope set is requested at consent time, so a scope added later needs a re-consent via `config(action="account_add")`.

### Calls hit the wrong account

Pass `account="<email>"` explicitly. `config(action="account_list")` shows which account is primary; `config(action="account_set_default")` changes it.
