# Telegram MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up better-telegram-mcp.

telegram runs as a local stdio server by default and as a self-hosted HTTP server. There is no hosted public instance, no browser setup form, and no OAuth authorization server: credentials come from environment variables or from the local `telegram auth` command, and are configured on the machine that runs the server.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, bot mode with `TELEGRAM_BOT_TOKEN`. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx hits PATH or Python version issues. |
| **3. Self-host** | `telegram --http` on a host you control | HTTP | One always-on server shared across devices and sessions, claude.ai web compatibility, per-user tokens. |

> **Mutually exclusive -- pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name -- and `npx`/`uvx` != `docker` != HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Option 1: Claude Code Plugin (Recommended, stdio Bot Mode)

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Optional (required for bot mode) | From @BotFather. User mode does not use this prompt; sign in with `telegram auth --phone` instead. |

### Steps

```bash
# Install from marketplace (includes skills: /setup-bot, /channel-post)
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-telegram-mcp@n24q02m-plugins
```

Paste your bot token when prompted. For user mode (read messages, browse chats), see "User mode" below.

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Option 2 (Docker stdio) or Option 3 (HTTP) below, DO NOT `/plugin install` this plugin -- pick Option 2 or Option 3 instead. All three methods are mutually exclusive (see Method overview).

## Option 2: Docker stdio (fallback)

> **Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-telegram-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Option 1 instead if you want full plugin features.

```bash
docker run -i --rm \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  n24q02m/telegram
```

Or as an MCP server config:

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

> A container has no terminal for the interactive OTP prompt, so Docker stdio is for bot mode. For user mode, authorize with `telegram auth --phone` on a host and run the server there (Option 3).

## User mode (MTProto)

User mode signs in as the user's Telegram account and needs a terminal for the OTP and 2FA prompts, so the user must run this command themselves (an agent cannot answer the prompts):

```bash
uvx --python 3.13 --from n24q02m-telegram telegram auth --phone +15551234567
```

1. Telegram sends an OTP to the **Telegram app** (not SMS); the user enters it at the prompt.
2. If the account has 2FA, the user enters the password at the prompt. It is never stored in the environment.
3. The Telethon session is stored on disk (`~/.telegram/`, mode 0600) and the credentials are saved encrypted.
4. Check with `telegram status`, then restart the server.

Also set `TELEGRAM_PHONE` (the same number) in the server's environment: the plugin's PreToolUse hook only checks the `TELEGRAM_PHONE` and `TELEGRAM_BOT_TOKEN` environment variables. Environment variables take precedence over saved credentials. The bundled public Telegram API pair is used by default, so no my.telegram.org registration is needed.

## Option 3: HTTP (self-host)

> **Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-telegram-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `better-telegram-mcp:setup-bot` skill will no longer be available. Use Option 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### Why HTTP?

- **claude.ai web compatibility** -- claude.ai supports HTTP MCP servers; stdio is desktop/CLI only.
- **One server, many sessions** -- a single HTTP server is shared across N Claude Code sessions instead of one stdio process per session.
- **Per-user tokens** -- `multi` auth gives each token holder their own Telegram namespace on a shared server.
- **Always-on persistent process** -- the Telegram session stays connected on the server.

### Configure and start

Mint the token hash (the token is read from stdin or a prompt, never from the command line), then write `~/.telegram/config.toml` on the server host:

```bash
printf '%s' "$TOKEN" | uvx --python 3.13 --from n24q02m-telegram telegram token hash   # prints scrypt$...
```

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

It serves MCP at `/mcp` and an unauthenticated `GET /health`. `no-auth` binds loopback only (a non-loopback host is refused, exit 2). `multi` reads per-user tokens from `users.toml`:

```toml
[users.alice]
token_hash = "scrypt$..."
enabled = true
namespace = "alice"
```

Edit `users.toml` on the host and restart the server; authorize each user's Telegram with `telegram auth --phone <+number> --user alice`. An invalid `config.toml` or `users.toml` prints one line and exits with status 2.

To reach the server from another machine, put it behind a TLS-terminating reverse proxy or a private network and use `token` or `multi` auth. Then point the MCP client at it:

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

## Environment Variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Bot mode | -- | Bot token from [@BotFather](https://t.me/BotFather) (format: `123456789:ABCdef...`) |
| `TELEGRAM_PHONE` | User mode | -- | Phone number in `+<country><number>` form |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | No | bundled public pair | Override the bundled Telegram API pair |
| `USE_BUNDLED_TELEGRAM_CLIENT` | No | `true` | Set to `false` to require your own API pair |
| `TELEGRAM_SESSION_NAME` | No | `default` | Telethon session file name |
| `TELEGRAM_DATA_DIR` | No | `~/.telegram` | Session and credential directory |
| `MCP_TRANSPORT` | No | `stdio` | Set to `http` (or pass `--http`) to start the HTTP server; `TRANSPORT_MODE` is an alias |

The bundled Telegram API pair is a public pair baked into the source. There is no `TELEGRAM_PASSWORD` variable.

## Mode Capabilities

| Feature | Bot | User |
|:--------|:---:|:----:|
| Send/Edit/Delete/Forward messages | Y | Y |
| Pin messages, React | Y | Y |
| Search messages, Browse history | -- | Y |
| List chats, Create groups/channels | -- | Y |
| Get chat info, Manage members | Y | Y |
| Send media (photo/file/voice/video) | Y | Y |
| Download media | -- | Y |
| Contacts (list/search/add/block) | -- | Y |

## Authentication

### Bot mode

Set the `TELEGRAM_BOT_TOKEN` env var (stdio), or save it once with `telegram auth --bot-token <token>` (the token is validated and saved). The server connects to the Bot API on startup.

### User mode

Run `telegram auth --phone <+number>` in a terminal (see "User mode (MTProto)" above). Re-authenticate by running it again; `telegram logout [--yes] [--user <ns>]` revokes the session and deletes the saved credentials.

## Verification

After setup, verify the server is working by calling the `config` tool:

```
config(action="status")
```

Expected: returns the mode (bot/user), connection and authorization state, and the current config.

Then test sending a message:

```
message(action="send", chat_id="me", text="Hello from MCP!")
```

Note: In bot mode, the bot can only message users who have started a conversation with it.
