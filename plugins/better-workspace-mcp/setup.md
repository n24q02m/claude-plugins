# Better Workspace MCP -- Manual Setup Guide

> **Beta.** The published artifacts are `0.1.0-beta.2` on npm (dist-tags `latest` and `beta`) and `:beta` on Docker Hub / GHCR. There is no stable tag yet, and there is no n24q02m-hosted instance -- HTTP mode is self-host only.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Quick local start, single workstation, your own Google OAuth client. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native `npx` hits PATH or Node version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-user, multi-device, team deploy, claude.ai web compatibility. |

> **⚠️ Mutually exclusive — pick ONE**: If you choose Method 2 or Method 3, do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in the `/mcp` dialog. Plugin matching is by **endpoint** (URL or command string), not by name — and `npx` ≠ `docker` ≠ HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's hooks. For full plugin features, use Method 1.

## Prerequisites

- **Node.js** >= 24.18.0 (Method 1) or Docker (Methods 2 and 3)
- A Google account, and a Google Cloud project where you can create an OAuth client

### Create the Google OAuth client

The server never ships a Google client of its own -- you bring your own, so the consent screen names your project and the quota is yours.

1. Open the [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth client ID**. The type depends on the mode you plan to run:
   - **Desktop app** for stdio (Methods 1 and 2). Desktop is the right type because the server receives the consent redirect on a [loopback address](https://developers.google.com/identity/protocols/oauth2/native-app), not on a public URL.
   - **Web application** for HTTP (Method 3). The redirect comes back to a fixed `/accounts/callback` on your host, and a Web client's redirect URI has to be registered with Google in advance.
3. Enable the Workspace APIs you plan to call on the same project (Docs, Drive, Calendar, Gmail, Sheets, Slides, Tasks, Chat, People, Forms — enable only what you need).
4. While the consent screen is unpublished, add yourself as a test user.

> A Desktop-app client secret is **not** a confidential secret in the OAuth sense — installed apps cannot keep one. It still identifies your project, so keep it out of public repos.

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
4. Restart Claude Code — the plugin auto-loads with your client injected.
5. On the **first run** the server opens the Google consent screen in your browser. Approve it once; the refresh token is stored encrypted on your machine, so later runs start without asking again.

Or configure it by hand in any MCP client:

```jsonc
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

## Method 2: Docker stdio (fallback)

> **⚠️ Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-workspace-mcp@n24q02m-plugins` first if you previously ran `/plugin install`.

The published image defaults to **HTTP** mode (`MCP_TRANSPORT=http`, port 8080 baked in) and there is no separate `:stdio` tag, so stdio over Docker means overriding the transport explicitly with `-e MCP_TRANSPORT=stdio`:

```bash
docker pull n24q02m/better-workspace-mcp:beta
```

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

Set the values in your shell profile:

```bash
export GOOGLE_OAUTH_CLIENT_ID="<your-client-id>.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="<your-client-secret>"
```

A container has no browser, so the first-run consent step cannot open one for you. Either authorize once via Method 1 first (the stored token is reused), or run HTTP mode, where each user consents through the server's own `/authorize`.

GHCR carries the same image if you prefer it: `ghcr.io/n24q02m/better-workspace-mcp:beta`.

## Why upgrade to HTTP mode?

Stdio mode is the default and works for single-user local development. Consider HTTP when you need any of:

- **Multi-user / team sharing** — each user's Google credentials live in their own bucket keyed by their JWT `sub`, so one deployment serves several people without them sharing an account
- **claude.ai web compatibility** — connect the server directly from claude.ai without a local CLI
- **1 server shared across N Claude Code sessions** — no per-session daemon proliferation
- **Multi-device credential sync** — credentials persist server-side; new devices just point at the URL
- **Browser consent without a local browser** — each user consents at the server's own `/authorize`

## Method 3: Docker HTTP (self-host)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: run `/plugin uninstall better-workspace-mcp@n24q02m-plugins` first if you previously ran `/plugin install`.

> **Switching transport vs. setting credentials**: the `userConfig` prompt only configures the OAuth client for stdio mode (Method 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below — a separate path from `userConfig`, not driven by the install prompt.

There is no hosted instance of this server. Run your own:

```bash
# HOST=0.0.0.0 binds all interfaces so the host can reach the container.
# PORT is already 8080 in the image; set it if you want a different one.
docker run -p 8080:8080 \
  -e HOST=0.0.0.0 \
  -e PUBLIC_URL=https://<your-host> \
  -e GOOGLE_OAUTH_CLIENT_ID=<your-web-client-id>.apps.googleusercontent.com \
  -e GOOGLE_OAUTH_CLIENT_SECRET=<your-web-client-secret> \
  -e MCP_RELAY_PASSWORD=<generated-32-byte-hex> \
  n24q02m/better-workspace-mcp:beta
```

This mode wants an OAuth client of type **Web application**, with `https://<your-host>/accounts/callback` registered as an authorized redirect URI. Authentication is OAuth 2.1 delegated to Google, and credentials are stored per JWT `sub`.

Point your MCP client at the host you deployed it on:

```json
{
  "mcpServers": {
    "better-workspace-mcp": {
      "type": "http",
      "url": "https://<your-host>/mcp"
    }
  }
}
```

### Edge auth: relay password

A public HTTP deployment exposes `<your-host>/authorize` to URL discovery. Without a gate in front of it, anyone who finds the URL can start a session on your deployment — per-user credential isolation limits what each session sees, it does not limit who gets one. Mint a relay password:

```bash
openssl rand -hex 32
# Save in your secret store as:
MCP_RELAY_PASSWORD=<generated-32-byte-hex>
```

Share it out-of-band with anyone you invite. They see a login form when first opening `/authorize`; the cookie then persists 24 hours.

**Single-user dev exception**: with `PUBLIC_URL=http://localhost:8080` you can leave `MCP_RELAY_PASSWORD` empty to disable the gate.

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | -- | OAuth client ID. Desktop app type for stdio, Web application type for HTTP. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | -- | Client secret of the same OAuth client. |
| `MCP_TRANSPORT` | No | `stdio` | `http` selects HTTP mode. `--http` on the command line and `TRANSPORT_MODE=http` do the same. |
| `PUBLIC_URL` | Yes (http) | -- | The server's public URL, used to build OAuth redirects. |
| `MCP_RELAY_PASSWORD` | Yes (http, public) | -- | Shared password gating `/authorize`. Optional only when `PUBLIC_URL` is localhost. |
| `CREDENTIAL_SECRET` | No (http) | auto-generated | Encryption key for the per-user credential store. If unset, a 32-byte secret is generated and persisted to a 0600 file; set it to keep stores decryptable across restarts. |
| `PORT` | No | `8080` in the image | Listen port (http mode). |
| `HOST` | No | -- | Bind address (http mode); set `0.0.0.0` to expose the container. |
| `MCP_AUTH_DISABLE` | No (http) | -- | Set to `1` to skip Bearer JWT verification. Only for deploys already behind an external auth gateway — never on a directly-exposed host. |
| `MCP_NO_BROWSER` / `NO_BROWSER` | No | -- | Suppress the first-run browser launch (headless environments). |
| `MCP_STORAGE_BACKEND` | No | filesystem | Credential storage backend. |
| `MCP_KV_BASE_URL` | No | -- | Base URL for the KV storage backend, when one is used. |

## Verification

After setup, check that the server answers at all — `time` needs no Google account:

```
Use the time tool with action "getCurrentTime".
```

Then confirm the credentials landed:

```
Use the config tool with action "status".
```

Before the first consent this reports `awaiting_setup`; afterwards it names the account the server is acting as.

## Multi-account

Every domain tool takes an `account` parameter — the email of the Google account the call acts as. Omit it and the call runs against the primary account. Accounts are managed through `config`: `account_add`, `account_list`, `account_remove`, `account_set_default`. See the [tools reference](/servers/better-workspace-mcp/tools/).

In HTTP mode, `account_add` completes through `/accounts/callback` on your host.

## Troubleshooting

### "Access blocked: This app is not verified"

Your consent screen is still unpublished. Add your Google account as a test user in the Cloud Console, or publish the consent screen.

### `redirect_uri_mismatch` in HTTP mode

The Web application client needs `https://<your-host>/accounts/callback` registered exactly, including scheme and any trailing path. A Desktop-type client will also produce this error in HTTP mode — HTTP needs a Web client.

### The browser never opens on first run

Containers and headless hosts have no browser. Authorize once via Method 1 on a workstation, or run HTTP mode and consent at the server's `/authorize`.

### A Workspace API returns 403

The API is probably not enabled on your Cloud project. Enable it under APIs & Services → Library, then retry — the scope set is requested at consent time, so a scope added later needs a re-consent via `config(action="account_add")`.

### Calls hit the wrong account

Pass `account="<email>"` explicitly. `config(action="account_list")` shows which account is primary; `config(action="account_set_default")` changes it.
