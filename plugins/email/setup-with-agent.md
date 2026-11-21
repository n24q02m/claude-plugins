# Email MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up the email MCP server.

email runs as a local stdio server by default and as a self-hosted HTTP server on request. There is no hosted public instance, no browser setup form, and no OAuth authorization server: credentials come from an accounts file, environment variables, or Outlook tokens saved by the local `email auth` command. Off loopback, HTTP clients authenticate with a bearer token; a loopback bind can run without one (`MCP_AUTH_MODE=no-auth`).

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Quick local start, single workstation, no HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native `npx` hits PATH or version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | One always-on server shared across devices and sessions, several users with separate mailboxes, or claude.ai web as a custom connector (conditions below). |

> **Mutually exclusive -- pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name -- and `npx` != `docker` != HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Option 1: Claude Code Plugin (Recommended -- stdio + userConfig prompt)

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `EMAIL_CREDENTIALS` | Required | Format: `user@gmail.com:app-password` (multi: comma-separated) |

### Steps

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install email@n24q02m-plugins
```

Paste your `EMAIL_CREDENTIALS` value when prompted. This installs the server with skills: `/inbox-review`, `/follow-up`. Restart Claude Code -- the plugin auto-loads with your credentials.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Option 2 (Docker stdio) or Option 3 (HTTP) below, DO NOT `/plugin install` this plugin -- pick Option 2 or Option 3 instead. All three methods are mutually exclusive (see Method overview).

## Option 2: Docker stdio (fallback)

> **Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall email@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Option 1 instead if you want full plugin features.

The image `n24q02m/email` (also `ghcr.io/n24q02m/email`) defaults to HTTP, so `MCP_TRANSPORT=stdio` is required:

```json
{
  "mcpServers": {
    "email": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "EMAIL_CREDENTIALS",
        "-e", "MCP_TRANSPORT=stdio",
        "n24q02m/email:latest"
      ]
    }
  }
}
```

Set `EMAIL_CREDENTIALS` in your shell profile or pass it inline.

## Option 3: Docker HTTP (self-host)

> **Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall email@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `email:inbox-review` skill will no longer be available. Use Option 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Why HTTP?

Switch to HTTP when you need any of:

- **claude.ai web** -- claude.ai uses a remote server that you add as a custom connector by its HTTPS URL. A connector added by URL is meant for a server hosted on the internet; for a server inside a private network, claude.ai needs an MCP tunnel, a research preview available to Claude Enterprise organizations by request (see [MCP tunnels](https://claude.com/docs/connectors/mcp-tunnels/overview)). To send the bearer token, choose **No sign-in** and add a request header `Authorization` with the value `Bearer <your-token>`. Request-header authentication is in beta and available to a limited set of organizations: if the connector dialog has no **Request headers** section, claude.ai cannot send the token, so it cannot use this server. See [Add a connector that isn't in the directory](https://claude.com/docs/connectors/custom/add-unlisted).
- **One server shared across N Claude Code sessions** -- no per-session process.
- **Always-on persistent process** -- the mail accounts and saved Outlook tokens live on the server.
- **Several users on one endpoint** -- each with their own bearer token and their own mailboxes (`MCP_AUTH_MODE=multi`, see the [setup guide](/servers/email/setup/)).

With `MCP_AUTH_MODE=token` (or unset with a hash), one shared bearer token protects the endpoint, and every client that holds the token sees the same server-wide accounts.

### Run the server

Mint the token hash first. The token is read from stdin, never from argv:

```bash
printf '%s' "$TOKEN" | npx @n24q02m/email token hash   # prints scrypt$...
```

```bash
export MCP_AUTH_TOKEN_HASH='scrypt$...'
export EMAIL_CREDENTIALS='you@gmail.com:app-password'
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e MCP_AUTH_TOKEN_HASH \
  -e EMAIL_CREDENTIALS \
  -e HOME=/data \
  -v email-data:/data \
  n24q02m/email:latest
```

The container binds `0.0.0.0`, so it refuses to start without a token hash (`MCP_AUTH_TOKEN_HASH`, or its older name `EMAIL_MCP_TOKEN_HASH`) or `MCP_AUTH_MODE=multi` with a users file; without auth the server only runs on loopback. `-v email-data:/data` keeps saved Outlook tokens across restarts. The repository also ships `docker-compose.http.yml`, which reads the hash from `EMAIL_MCP_TOKEN_HASH` and publishes the server on `127.0.0.1:8082` only. To serve other machines, put your own TLS reverse proxy in front of it.

### Point your MCP client at the server

Clients send the raw token as `Authorization: Bearer <token>` to `https://<your-host>/mcp`.

#### Claude Code (settings.json)

```json
{
  "mcpServers": {
    "email": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

#### Codex CLI (config.toml)

```toml
[mcp_servers.email]
type = "http"
url = "https://<your-host>/mcp"
http_headers = { Authorization = "Bearer <your-token>" }
```

#### OpenCode (opencode.json)

```json
{
  "mcpServers": {
    "email": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

Keep the token in the client's secret store or environment, not in a committed file.

## Environment Variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `EMAIL_ACCOUNTS_FILE` | Alternative | `~/.email/accounts.toml` when it exists | Path to a TOML accounts file; wins over `EMAIL_CREDENTIALS` and `EMAIL_USER`. `off`, `none`, `false` or `0` disables the lookup. |
| `EMAIL_CREDENTIALS` | Alternative | -- | `email:app-password` per account, comma-separated for multiple accounts. Optional custom IMAP host/port: `email:password:imap_host:imap_port`. |
| `EMAIL_USER` | Alternative (single account) | -- | Email address; used with `EMAIL_APP_PASSWORD`. |
| `EMAIL_APP_PASSWORD` | Alternative (single account) | -- | App password (Gmail/Yahoo/iCloud) or Outlook App Password; used with `EMAIL_USER`. |
| `EMAIL_DATA_DIR` | No | `$HOME` | Base directory for the server's own files; saved Outlook tokens live in `<dir>/.email/tokens.json`. |
| `MCP_TRANSPORT` | No | `stdio` (npx), `http` (Docker image) | Set to `http` (or pass `--http`) to run the HTTP server. `TRANSPORT_MODE` is an accepted alias. |
| `MCP_AUTH_MODE` | No (HTTP) | -- | `token`, `multi` or `no-auth`. Unset: a token hash selects `token`; without one HTTP runs unauthenticated only on loopback. |
| `MCP_AUTH_TOKEN_HASH` | HTTP `token` mode | -- | scrypt hash of the shared Bearer token, from `email token hash`. `EMAIL_MCP_TOKEN_HASH` is the older name and still works. |
| `MCP_USERS_FILE` | No (HTTP `multi`) | `~/.hull/users.toml` | users.toml token table for multi mode. |
| `PORT` | No | `0` (OS-assigned) | HTTP port; set explicitly (for example `8080`) to bind a fixed port. |
| `HOST` | No | `0.0.0.0` | HTTP bind address. |
| `OUTLOOK_CLIENT_ID` | No | bundled public client | Override the Azure AD public client for Outlook OAuth2. |
| `OUTLOOK_EMAIL` | No | -- | Workaround when the Microsoft device-code response omits the email field. |
| `OUTLOOK_TENANT` | No | `consumers` (stdio/CLI), `common` (HTTP device-code) | Directory to sign in against; set `common` or a tenant GUID for a work/school mailbox. |
| `OUTLOOK_SCOPES` | No | IMAP + SMTP + `offline_access` | Space-separated scope list; narrow it for a read-only deployment. |
| `OUTLOOK_EXTRA_DOMAINS` | No | -- | Comma-separated extra domains routed to OAuth instead of a password. |

## Authentication

### Gmail, Yahoo, iCloud (App Passwords)

Both transports accept **App Passwords** (not your regular password) in `EMAIL_CREDENTIALS`:
- **Gmail**: Enable 2FA, then create at https://myaccount.google.com/apppasswords
- **Yahoo**: Enable 2FA, then create at https://login.yahoo.com/account/security/app-passwords
- **iCloud**: Go to https://appleid.apple.com -> Sign-In and Security -> App-Specific Passwords

### Outlook / Hotmail / Live

Either put an Outlook **App Password** in `EMAIL_CREDENTIALS` (Account Settings -> Security -> Advanced security options -> App passwords), or sign in with OAuth2 device code once, on the machine that runs the server:

```bash
npx @n24q02m/email auth outlook you@outlook.com
```

1. The CLI prints a device code and a Microsoft login URL.
2. Open the URL and enter the code.
3. Sign in and authorize.
4. Tokens are saved to `~/.email/tokens.json` (`/data/.email/tokens.json` in Docker). Sign out with `email logout [<address>]`.

The bundled public Azure client needs no app registration of your own. A Microsoft 365 work or school mailbox, including one on your own domain, needs `OUTLOOK_TENANT=common` (or a tenant GUID) and `OUTLOOK_EXTRA_DOMAINS=company.com`.

### Custom IMAP

```
EMAIL_CREDENTIALS=user@custom.com:password:imap.custom.com
EMAIL_CREDENTIALS=user@custom.com:password:imap.custom.com:1993
```

The second form sets a port; a non-993 port is plaintext/STARTTLS. `localhost` is accepted as a host for a local IMAP proxy.

## Verification

After setup, verify the server is working:

```
Use the config tool with action "status" to check the credential state, then the folders tool with action "list" to verify the server can connect to your email account.
```

Expected: `state` is not `awaiting_setup`, and `folders` returns a list of mailbox folders (INBOX, Sent, Drafts, etc.).
