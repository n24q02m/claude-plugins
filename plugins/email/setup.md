# Email MCP -- Manual Setup Guide

email runs as a local stdio server by default and as a single-user HTTP server for self-hosting. There is no hosted public instance, no browser setup form, and no OAuth authorization server: credentials come from environment variables, or from Outlook tokens saved by the local `email auth` command.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, no HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx/npx hits PATH or version issues. |
| **3. Self-host** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | One always-on server shared across devices and sessions, claude.ai web compatibility. |

> **Mutually exclusive -- pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name -- and `npx`/`uvx` != `docker` != HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Prerequisites

- **Node.js** >= 24.21.0 (Method 1 and the `email auth` command)
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
   /plugin install better-email-mcp@n24q02m-plugins
   ```
4. Restart Claude Code -- the plugin auto-loads with your credentials injected.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Method 2 (Docker stdio) or Method 3 (HTTP) below, DO NOT `/plugin install` this plugin -- pick Method 2 or Method 3 instead. All three methods are mutually exclusive (see Method overview).

## Method 2: Docker stdio (fallback)

> **Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-email-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
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

> **Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-email-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `better-email-mcp:inbox-review` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Why HTTP?

Stdio mode is the default and works for single-user local use. Switch to HTTP when you need any of:

- **claude.ai web compatibility** -- claude.ai connects to HTTP MCP servers; stdio is desktop/CLI only.
- **One server shared across N Claude Code sessions** -- no per-session process.
- **Always-on persistent process** -- the mail accounts and saved Outlook tokens live on the server.

HTTP mode is **single-user**: one shared Bearer token protects the endpoint, and every client that holds the token sees the same accounts. There is no per-user credential store.

### Mint the Bearer token hash

The server stores only a scrypt hash of the token. The token is read from stdin, never from argv:

```bash
printf '%s' "$TOKEN" | npx @n24q02m/email token hash
# prints scrypt$...  -> use as EMAIL_MCP_TOKEN_HASH
```

`EMAIL_MCP_TOKEN_HASH` is required whenever the server binds a non-loopback address (every container does). Without it the server runs unauthenticated only on loopback and refuses to bind anything else.

### Run with docker

```bash
export EMAIL_MCP_TOKEN_HASH='scrypt$...'
export EMAIL_CREDENTIALS='you@gmail.com:app-password'
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e EMAIL_MCP_TOKEN_HASH \
  -e EMAIL_CREDENTIALS \
  -e HOME=/data \
  -v email-data:/data \
  n24q02m/email:latest
```

`-v email-data:/data` keeps saved Outlook tokens (`/data/.better-email-mcp/`) across restarts. The repository also ships `docker-compose.http.yml`, which builds the HTTP image and publishes it on `127.0.0.1:8082` only. To serve other machines, put your own TLS reverse proxy in front of it.

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
4. Tokens are saved to `~/.better-email-mcp/tokens.json` (mode 0600 on POSIX). Sign out with `email logout [<address>]`.

The bundled public Azure client (`d56f8c71-9f7c-43f4-9934-be29cb6e77b0`, Thunderbird pattern) needs no Azure app registration of your own. Pass `--client-id=<id>` or set `OUTLOOK_CLIENT_ID` to use your own.

A Microsoft 365 work or school mailbox, including one on your own domain, signs in through Entra ID and cannot use an App Password. Set `OUTLOOK_TENANT=common` (or a tenant GUID / verified domain) and `OUTLOOK_EXTRA_DOMAINS=company.com`.

## Credential setup

Credential resolution order at startup: environment variables, then a legacy `config.enc` (read-only), then saved Outlook tokens. If none is found the server is in state `awaiting_setup`; a stdio server with no credentials prints an error to stderr and exits with code 1, and `config(action="setup_start")` returns the steps.

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
| `EMAIL_CREDENTIALS` | Yes (unless using the alternatives) | -- | `email:app-password` per account, comma-separated for multiple accounts. Optional custom IMAP host/port: `email:password:imap_host:imap_port`. |
| `EMAIL_USER` | Alternative (single account) | -- | Email address; used with `EMAIL_APP_PASSWORD`. |
| `EMAIL_APP_PASSWORD` | Alternative (single account) | -- | App password (Gmail/Yahoo/iCloud) or Outlook App Password; used with `EMAIL_USER`. |
| `MCP_TRANSPORT` | No | `stdio` (npx), `http` (Docker image) | Set to `http` (or pass `--http`) to run the HTTP server. `TRANSPORT_MODE` is an accepted alias. |
| `EMAIL_MCP_TOKEN_HASH` | HTTP, non-loopback | -- | scrypt hash of the shared Bearer token, from `email token hash`. |
| `PORT` | No | `0` (OS-assigned) | HTTP port; set explicitly (for example `8080`) to bind a fixed port. |
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
| iCloud / Me.com | App-Specific Password | Auto (skipped) |
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
