# Telegram MCP -- Manual Setup Guide

telegram runs as a local stdio server by default and as a self-hosted HTTP server. There is no hosted public instance, no browser setup form, and no OAuth authorization server: credentials come from environment variables or from the local `telegram auth` command, and are configured on the machine that runs the server.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, bot mode with `TELEGRAM_BOT_TOKEN`. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx hits PATH or Python version issues. |
| **3. Self-host** | `telegram --http` on a host you control | HTTP | One always-on server shared across devices and sessions, claude.ai web compatibility, per-user tokens. |

> **Mutually exclusive -- pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name -- and `npx`/`uvx` != `docker` != HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Prerequisites

- **Python 3.13** (3.14+ is NOT supported)
- `uv` or `uvx` installed ([docs](https://docs.astral.sh/uv/getting-started/installation/))
- Docker (optional, for Method 2)
- A Telegram account and either a bot token (bot mode) or a phone number (user mode)

## Method 1: Plugin Install (stdio, Bot Mode)

For Claude Code users, the plugin approach is the simplest.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Optional (required for bot mode) | From @BotFather. User mode does not use this prompt; sign in with `telegram auth --phone` instead (see "User mode" below). |

### Steps

1. Get a bot token from [@BotFather](https://t.me/BotFather):
   - Open Telegram, send `/newbot` to @BotFather
   - Follow prompts to name your bot
   - Copy the token (format: `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`)

2. Open Claude Code and install the plugin (Claude Code prompts for `TELEGRAM_BOT_TOKEN`):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-telegram-mcp@n24q02m-plugins
   ```

3. Restart Claude Code -- the server starts in stdio bot mode with the token injected.

> **Need user mode (read messages, browse chats, manage groups)?** Bot tokens cannot do this. See "User mode" below.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Method 2 (Docker stdio) or Method 3 (HTTP) below, DO NOT `/plugin install` this plugin -- pick Method 2 or Method 3 instead. All three methods are mutually exclusive (see Method overview).

## Method 2: Docker stdio (fallback)

> **Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-telegram-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Method 1 instead if you want full plugin features.

1. Pull the image (Docker Hub `n24q02m/telegram`, also on GHCR as `ghcr.io/n24q02m/telegram`):
   ```bash
   docker pull n24q02m/telegram:latest
   ```

2. Run with bot token:
   ```bash
   docker run -i --rm \
     -e TELEGRAM_BOT_TOKEN=your_bot_token \
     n24q02m/telegram
   ```

### MCP Client Config (Docker)

```json
{
  "mcpServers": {
    "telegram": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TELEGRAM_BOT_TOKEN",
        "n24q02m/telegram"
      ]
    }
  }
}
```

> A container has no terminal for the interactive OTP prompt, so the Docker stdio setup is for bot mode. For user mode, authorize with `telegram auth --phone` on a host and run the server there (Method 3).

## User mode (MTProto)

User mode signs in as your Telegram account, so it needs a terminal for the OTP and 2FA prompts. Run this once, on the machine that runs the server:

```bash
uvx --python 3.13 --from n24q02m-telegram telegram auth --phone +15551234567
```

1. Telegram sends an OTP to your **Telegram app** (not SMS); enter it at the prompt.
2. If the account has 2FA, enter the password at the prompt. It is never stored in an environment variable.
3. The Telethon session is stored on disk (`~/.telegram/`, mode 0600) and the credentials are saved encrypted.
4. Check with `telegram status`, then restart the server.

Set `TELEGRAM_PHONE` (the same number) in the server's environment as well: the plugin's PreToolUse hook only checks the `TELEGRAM_PHONE` and `TELEGRAM_BOT_TOKEN` environment variables. Environment variables take precedence over saved credentials.

The bundled public Telegram API pair is used by default, so you do **not** need to register at my.telegram.org. Set `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` to use your own, or `USE_BUNDLED_TELEGRAM_CLIENT=false` to require your own.

## Method 3: HTTP (self-host)

> **Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-telegram-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `better-telegram-mcp:setup-bot` skill will no longer be available. Use Method 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Why HTTP?

Stdio is the simplest path. Switch to HTTP when you need any of:

- **claude.ai web compatibility** -- claude.ai supports HTTP MCP servers; stdio is desktop/CLI only.
- **One server, many sessions** -- a single HTTP server is shared across N Claude Code sessions instead of one stdio process per session.
- **Per-user tokens** -- `multi` auth gives each token holder their own Telegram namespace on a shared server.
- **Always-on persistent process** -- the Telegram session stays connected on the server.

### Configure and start

Mint the token hash first. The token is read from stdin or a prompt, never from the command line:

```bash
printf '%s' "$TOKEN" | uvx --python 3.13 --from n24q02m-telegram telegram token hash   # prints scrypt$...
```

Settings live in the host-owned `~/.telegram/config.toml`. MCP clients never see it:

```toml
[server]
host = "127.0.0.1"   # default; --host overrides
port = 8000          # default; --port overrides
auth = "token"       # "no-auth" | "token" | "multi"
token_hash = "scrypt$..."
# users_file = "users.toml"   # multi mode; defaults to ~/.telegram/users.toml
# rpm = 60                    # optional per-client rate limit
```

Authorize Telegram for the default credentials (`telegram auth --bot-token <token>` or `telegram auth --phone <+number>`), then start the server:

```bash
uvx --python 3.13 --from n24q02m-telegram telegram --http [--host H] [--port P]
```

It serves MCP at `/mcp` and an unauthenticated `GET /health`. An invalid `config.toml` or `users.toml` prints one line to stderr and exits with status 2.

| `auth` | Who can connect | Credentials used |
|---|---|---|
| `no-auth` | Anyone who can reach the port; loopback binds only (a non-loopback host is refused) | The default credentials |
| `token` | Clients sending `Authorization: Bearer <token>` that matches `token_hash` | The default credentials |
| `multi` | Users listed in `users.toml`, each with their own token | Each user's own namespace |

### Multiple users (`auth = "multi"`)

Users are administered on the host by editing `users.toml` and restarting the server:

```toml
[users.alice]
token_hash = "scrypt$..."
enabled = true
namespace = "alice"
```

Then authorize that user's Telegram on the server machine:

```bash
telegram auth --phone +15551234567 --user alice
```

### Reaching the server from another machine

Put it behind a TLS-terminating reverse proxy or a private network, and use `token` or `multi` auth. Then point clients at it with the raw token:

```json
{
  "mcpServers": {
    "telegram": {
      "type": "http",
      "url": "https://<your-host>/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

Keep the token in the client's secret store or environment, not in a committed file.

> Python 3.14+ is **not supported** because Telethon and `cryptg` have not yet shipped 3.14 wheels.

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Bot mode | -- | Bot token from @BotFather |
| `TELEGRAM_PHONE` | User mode | -- | Phone number in `+<country><number>` form |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | No | bundled public pair | Override the bundled Telegram API pair |
| `USE_BUNDLED_TELEGRAM_CLIENT` | No | `true` | Set to `false` to require your own API pair |
| `TELEGRAM_SESSION_NAME` | No | `default` | Telethon session file name |
| `TELEGRAM_DATA_DIR` | No | `~/.telegram` | Session and credential directory |
| `MCP_TRANSPORT` | No | `stdio` | Set to `http` (or pass `--http`) to start the HTTP server; `TRANSPORT_MODE` is an alias |

There is no `TELEGRAM_PASSWORD` variable: `telegram auth` prompts for the 2FA password and never stores it in the environment.

## Troubleshooting

### Bot cannot send messages

Bots can only message users who have started a conversation with the bot first. Have the target user send `/start` to your bot.

### Bot token does not work

Verify the token format: `<bot_id>:<token_secret>` (e.g., `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`). Re-issue from @BotFather if needed.

### Need to read messages or browse chat history

Bot mode cannot read messages or browse chats -- the Bot API does not expose these capabilities. Authenticate as a user with `telegram auth --phone` (see "User mode").

### OTP code not received

The OTP code is sent to the **Telegram app** as a message from "Telegram" service notifications, not via SMS. Open your Telegram app on any device.

### Session expired

Re-run `telegram auth --phone <+number>` (add `--user <namespace>` for a `multi` user) and restart the server.

### 2FA password prompt

The 2FA password is entered at the `telegram auth` terminal prompt. It is never stored in environment variables or files.

### "FloodWaitError" from Telegram

Telegram rate-limits API calls. Wait the indicated time before retrying. The server handles this automatically for most operations.
