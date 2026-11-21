# Email MCP -- Manual Setup Guide

email runs as a local stdio server by default and as a self-hosted HTTP server on request. There is no hosted public instance, no browser setup form, and no OAuth authorization server: credentials come from an accounts file, environment variables, or Outlook tokens saved by the local `email auth` command. Off loopback, HTTP clients authenticate with a bearer token; a loopback bind can run without one (`MCP_AUTH_MODE=no-auth`).

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`npx`) | stdio | Quick local start, single workstation, no HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native `npx` hits PATH or version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | One always-on server shared across devices and sessions, several users with separate mailboxes, or claude.ai web as a custom connector (conditions below). |

> **Mutually exclusive -- pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name -- and `npx` != `docker` != HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Prerequisites

- **Node.js** >= 24.22.3 (Method 1 and the `email auth` command)
- Docker (Methods 2 and 3)
- An email account with an App Password enabled (Gmail, Yahoo, iCloud, Zoho), or an Outlook/Hotmail/Live account (App Password, or the OAuth device-code sign-in with the bundled public client)

### Create App Passwords

App Passwords are required for App-Password providers (NOT your regular password):

- **Gmail**: Enable 2FA at https://myaccount.google.com/security, then create an App Password at https://myaccount.google.com/apppasswords (Settings -> Security -> 2-Step Verification -> App passwords)
- **Yahoo**: Enable 2FA, then go to https://login.yahoo.com/account/security/app-passwords
- **iCloud / Me.com**: Go to https://appleid.apple.com -> Sign-In and Security -> App-Specific Passwords
- **Outlook / Hotmail / Live**: Either an App Password (Account Settings -> Security -> Advanced security options -> App passwords), or no password at all: run `email auth outlook <address>` once (see "Outlook sign-in" below).

## Method 1: Claude Code Plugin (Recommended)

Plugin install runs in **stdio mode** with credentials provided via the `userConfig` install prompt.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `EMAIL_CREDENTIALS` | Required | Format: `user@gmail.com:app-password` (multi: comma-separated) |

### Steps

1. Prepare an App Password for each account (see "Create App Passwords" above).
2. Open Claude Code in your terminal.
3. Install the plugin (Claude Code prompts for `EMAIL_CREDENTIALS`):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install email@n24q02m-plugins
   ```
4. Restart Claude Code -- the plugin auto-loads with your credentials injected.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Method 2 (Docker stdio) or Method 3 (HTTP) below, DO NOT `/plugin install` this plugin -- pick Method 2 or Method 3 instead. All three methods are mutually exclusive (see Method overview).

## Method 2: Docker stdio (fallback)

> **Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall email@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Method 1 instead if you want full plugin features.

1. Pull the image (Docker Hub `n24q02m/email`, also on GHCR as `ghcr.io/n24q02m/email`):
   ```bash
   docker pull n24q02m/email:latest
   ```

2. Add to your MCP client config. The image defaults to HTTP, so `MCP_TRANSPORT=stdio` is required:
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

3. Set the credentials in your shell profile. `EMAIL_CREDENTIALS` is **comma-separated between accounts** and **colon-separated within** each account (`email:password`, plus an optional `:imap_host:imap_port` for custom domains):
   ```bash
   export EMAIL_CREDENTIALS="user1@gmail.com:app_password1,user2@custom.com:password2:imap.custom.com"
   ```

## Method 3: Docker HTTP (self-host)

> **Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall email@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `email:inbox-review` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Why HTTP?

Stdio mode is the default and works for single-user local use. Switch to HTTP when you need any of:

- **claude.ai web** -- claude.ai uses a remote server that you add as a custom connector by its HTTPS URL. A connector added by URL is meant for a server hosted on the internet; for a server inside a private network, claude.ai needs an MCP tunnel, a research preview available to Claude Enterprise organizations by request (see [MCP tunnels](https://claude.com/docs/connectors/mcp-tunnels/overview)). To send the bearer token, choose **No sign-in** and add a request header `Authorization` with the value `Bearer <your-token>`. Request-header authentication is in beta and available to a limited set of organizations: if the connector dialog has no **Request headers** section, claude.ai cannot send the token, so it cannot use this server. See [Add a connector that isn't in the directory](https://claude.com/docs/connectors/custom/add-unlisted).
- **One server shared across N Claude Code sessions** -- no per-session process.
- **Always-on persistent process** -- the mail accounts and saved Outlook tokens live on the server.
- **Several users on one endpoint** -- each with their own bearer token and their own mailboxes (`MCP_AUTH_MODE=multi`).

### Auth modes

Clients send a bearer token unless the mode is `no-auth`. What the token reaches depends on `MCP_AUTH_MODE`:

| `MCP_AUTH_MODE` | Who can call | Which mailboxes a call reaches |
|---|---|---|
| `token` (or unset with a hash) | anyone holding the one shared token (`MCP_AUTH_TOKEN_HASH`) | the server-wide accounts (accounts file, env vars, `email auth outlook`) |
| `multi` | each user in a hull `users.toml` token table (`MCP_USERS_FILE`) | only that user's own namespace: `users/<namespace>/accounts.toml` and `users/<namespace>/tokens.json` under `<base>/.email/` (base: `EMAIL_DATA_DIR`, else `$HOME`) |
| `no-auth` (or unset, no hash, loopback bind) | anything that can reach the loopback port | the server-wide accounts |

In `token` and `multi` mode a request with no token or a wrong one gets `401`. The server binds `0.0.0.0` unless `HOST` says otherwise, and with no mode and no hash it refuses to start on a non-loopback bind, so every container needs a token hash or a users file.

### Mint the Bearer token hash

The server stores only a scrypt hash of the token. The token is read from stdin, never from argv:

```bash
printf '%s' "$TOKEN" | npx @n24q02m/email token hash
# prints scrypt$...  -> use as MCP_AUTH_TOKEN_HASH
```

`EMAIL_MCP_TOKEN_HASH` is the older name of `MCP_AUTH_TOKEN_HASH` and still works; `MCP_AUTH_TOKEN_HASH` wins when both are set.

### Run with docker (shared token)

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

`-v email-data:/data` keeps saved Outlook tokens (`/data/.email/`) across restarts. The repository also ships `docker-compose.http.yml`, which builds the `http` image target, reads the hash from `EMAIL_MCP_TOKEN_HASH`, and publishes the server on `127.0.0.1:8082` only. To serve other machines, put your own TLS reverse proxy in front of it.

### Several users (multi mode)

Each user gets their own bearer token and their own mailboxes; no user can see another's, and the server-wide accounts (`EMAIL_ACCOUNTS_FILE`, `EMAIL_CREDENTIALS`, `EMAIL_USER`) are not served to anyone in this mode. Provisioning is host-side:

```toml
# users.toml (MCP_USERS_FILE, default ~/.hull/users.toml)
[users.alice]
token_hash = "scrypt$..."   # printf '%s' "$ALICE_TOKEN" | email token hash
namespace = "alice"

[users.bob]
token_hash = "scrypt$..."
namespace = "bob"
[users.bob.limits]
rpm = 60
```

Then give each namespace its mailboxes under `<base>/.email/`, in the accounts file schema (see "Accounts file" below):

```bash
# <base>/.email/users/alice/accounts.toml  (in Docker: /data/.email/users/alice/accounts.toml)
# and/or an Outlook grant for one namespace:
email auth outlook alice@outlook.com --user alice
MCP_AUTH_MODE=multi MCP_USERS_FILE=/data/users.toml email --http
```

Accounts are re-read on every tool call, so an edited `accounts.toml` applies without a restart. A namespace is one path segment (letters, digits, `_`, `-`). The `config` tool reports a caller's own accounts; `setup_reset` and `setup_complete` are refused for a multi-user caller.

### Point clients at the server

Clients send the raw token as `Authorization: Bearer <token>` to `https://<your-host>/mcp`:

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

Keep the token in your client's secret store or environment, not in a committed file.

## Outlook sign-in

Outlook, Hotmail, and Live accounts can use OAuth2 device code instead of an App Password. Run this once on the machine that runs the server (inside the container for Method 3):

```bash
npx @n24q02m/email auth outlook you@outlook.com
```

1. The CLI prints a device code and a Microsoft login URL.
2. Open the URL in a browser and enter the code.
3. Sign in and authorize the app.
4. Tokens are saved to `~/.email/tokens.json` (mode 0600 on POSIX; `/data/.email/tokens.json` in Docker). With `--user <namespace>` they go to that HTTP multi-user namespace instead. Sign out with `email logout [<address>]`.

A token file from an earlier release (`~/.better-email-mcp/tokens.json`) is copied forward on the next start; the old file is left in place.

The bundled public Azure client (`d56f8c71-9f7c-43f4-9934-be29cb6e77b0`, Thunderbird pattern) needs no Azure app registration of your own. Pass `--client-id=<id>` or set `OUTLOOK_CLIENT_ID` to use your own.

A Microsoft 365 work or school mailbox, including one on your own domain, signs in through Entra ID and cannot use an App Password. Set `OUTLOOK_TENANT=common` (or a tenant GUID / verified domain) and `OUTLOOK_EXTRA_DOMAINS=company.com`.

## Credential setup

Credential resolution order at startup, highest first: the accounts file, `EMAIL_CREDENTIALS`, `EMAIL_USER` + `EMAIL_APP_PASSWORD`, a legacy encrypted `config.enc` (read-only), then saved Outlook tokens. If none is found the server is in state `awaiting_setup`; a stdio server with no credentials prints an error to stderr and exits with code 1, and `config(action="setup_start")` returns the steps.

### Single account

```bash
EMAIL_USER=you@gmail.com
EMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

`EMAIL_USER` + `EMAIL_APP_PASSWORD` are merged into `EMAIL_CREDENTIALS` at boot. The provider is detected from the email domain.

### Multiple accounts

```bash
EMAIL_CREDENTIALS=user1@gmail.com:pass1,user2@outlook.com:pass2,user3@yahoo.com:pass3
```

With two or more enabled accounts, `messages` search and `folders` list fan out over every account; every other action works on one mailbox and requires `account`, and omitting it is rejected with the list of accounts to choose from.

### Accounts file

For more than a couple of mailboxes, point `EMAIL_ACCOUNTS_FILE` at a TOML file. When it is unset, `~/.email/accounts.toml` is used if it exists; `EMAIL_ACCOUNTS_FILE=off` (or `none`/`false`/`0`) disables the lookup.

```toml
[accounts.personal]
email = "you@gmail.com"
password = "app-password"

[accounts.work]
email = "me@company.com"
password = "app-password"
imap_host = "imap.company.com"    # optional; skips provider auto-discovery
imap_port = 993                   # optional, default 993 with a custom host
smtp_host = "smtp.company.com"    # optional, default: guessed from imap_host
smtp_port = 587                   # optional
smtp_security = "starttls"        # optional: tls | ssl | starttls | none
aliases = ["team@company.com"]    # optional; other addresses this mailbox may send as
enabled = true                    # optional; false keeps the row but skips it
```

Validation is strict: unknown keys, a duplicate mailbox, an empty file, and a row whose IMAP/SMTP cannot be resolved are errors that name the file. A file that is selected explicitly and cannot be read is a boot error rather than a silent fallback.

### Custom IMAP host

For providers not auto-detected, append the host (and optionally the port):

```bash
# Custom hostname (default port 993, implicit TLS)
EMAIL_CREDENTIALS=user@custom.com:password:imap.custom.com

# Custom hostname with a custom port (a non-993 port is plaintext/STARTTLS)
EMAIL_CREDENTIALS=user@custom.com:password:imap.custom.com:1993

# Local IMAP proxy -- "localhost" is accepted as a host
EMAIL_CREDENTIALS=user@custom.com:password:localhost:1993
```

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `EMAIL_ACCOUNTS_FILE` | Alternative | `~/.email/accounts.toml` when it exists | Path to the accounts file; wins over `EMAIL_CREDENTIALS` and `EMAIL_USER`. `off`, `none`, `false` or `0` disables the lookup. |
| `EMAIL_CREDENTIALS` | Alternative | -- | `email:app-password` per account, comma-separated for multiple accounts. Optional custom IMAP host/port: `email:password:imap_host:imap_port`. |
| `EMAIL_USER` | Alternative (single account) | -- | Email address; used with `EMAIL_APP_PASSWORD`. |
| `EMAIL_APP_PASSWORD` | Alternative (single account) | -- | App password (Gmail/Yahoo/iCloud) or Outlook App Password; used with `EMAIL_USER`. |
| `EMAIL_DATA_DIR` | No | `$HOME` | Base directory for the server's own files; saved Outlook tokens live in `<dir>/.email/tokens.json`. |
| `EMAIL_MCP_DRAFT_ONLY` | No | -- | Set to `1` for agents that read untrusted mail: `new`/`reply`/`forward` save to Drafts instead of sending, and `move`/`archive`/`trash`/`setup_reset` are removed from the tool list. |
| `MCP_TRANSPORT` | No | `stdio` (npx), `http` (Docker image) | Set to `http` (or pass `--http`) to run the HTTP server. `TRANSPORT_MODE` is an accepted alias. |
| `MCP_AUTH_MODE` | No (HTTP) | -- | `token`, `multi` or `no-auth`. Unset: a token hash selects `token`; without one HTTP runs unauthenticated only on loopback and refuses any other bind. |
| `MCP_AUTH_TOKEN_HASH` | HTTP `token` mode | -- | scrypt hash of the shared Bearer token, from `email token hash`. `EMAIL_MCP_TOKEN_HASH` is the older name and still works. |
| `MCP_RPM` | No (HTTP `token`) | -- | Per-minute request cap for the shared token. |
| `MCP_USERS_FILE` | No (HTTP `multi`) | `~/.hull/users.toml` | users.toml token table: one `[users.<id>]` row per user with `token_hash`, `namespace`, optional `enabled` and `[users.<id>.limits] rpm`. |
| `PORT` / `MCP_PORT` | No | `0` (OS-assigned) | HTTP port; `PORT` wins, then `MCP_PORT`. Set explicitly (for example `8080`) to bind a fixed port. The Docker `http` image sets `MCP_PORT=8080`. |
| `HOST` | No | `0.0.0.0` | HTTP bind address. |
| `OUTLOOK_CLIENT_ID` | No | bundled public client | Override the Azure AD public client for Outlook OAuth2. |
| `OUTLOOK_EMAIL` | No | -- | Workaround when the Microsoft device-code response omits the email field. |
| `OUTLOOK_TENANT` | No | `consumers` (stdio/CLI), `common` (HTTP device-code) | Directory to sign in against; set `common` or a tenant GUID for a work/school mailbox. |
| `OUTLOOK_SCOPES` | No | IMAP + SMTP + `offline_access` | Space-separated scope list; narrow it for a read-only deployment. |
| `OUTLOOK_EXTRA_DOMAINS` | No | -- | Comma-separated extra domains routed to OAuth instead of a password. |

## Supported Providers

| Provider | Auth | Save-to-Sent |
|:---------|:-----|:-------------|
| Gmail | App Password | Auto (skipped -- Gmail saves sent mail) |
| Yahoo | App Password | Auto (skipped) |
| iCloud / Me.com | App-Specific Password | IMAP APPEND |
| Outlook / Hotmail / Live | App Password, or OAuth2 device code via `email auth` | IMAP APPEND |
| Zoho | App Password | IMAP APPEND |
| ProtonMail | ProtonMail Bridge | IMAP APPEND |
| Custom IMAP | `email:pass:imap.host[:port]` in `EMAIL_CREDENTIALS` | IMAP APPEND |

## Troubleshooting

### "Authentication failed" for Gmail

- Ensure you created an **App Password**, not using your regular Google password.
- Verify 2-Step Verification is enabled on your Google account.
- The App Password format is 16 characters (often shown as 4 groups of 4 with spaces -- both with and without spaces work).

### "Authentication failed" for Yahoo

- Create an App Password at https://login.yahoo.com/account/security/app-passwords
- Yahoo App Passwords bypass "Allow apps that use less secure sign in" settings.

### Outlook sign-in does not start

- Run `email auth outlook <address>` and watch the terminal for the Microsoft login URL and code; the server itself never prompts.
- The bundled public client works out of the box; you only need `OUTLOOK_CLIENT_ID` for a custom Azure app.
- For a work/school mailbox set `OUTLOOK_TENANT` and `OUTLOOK_EXTRA_DOMAINS`.

### "IMAP connection timeout"

- Check your internet connection.
- For custom IMAP hosts, verify the hostname and that port 993 (IMAPS) is accessible.
- Some corporate networks block IMAP. Try from a different network.

### Multiple accounts: only one account works

- Ensure comma separation with no spaces: `user1@gmail.com:pass1,user2@yahoo.com:pass2`
- Each account must have valid credentials independently.
