# Telegram MCP -- Troubleshooting

Common issues specific to better-telegram-mcp. For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx --python 3.13 --from n24q02m-telegram==<X.Y.0bN> telegram
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `==<version>` pin to return to the latest stable.

## Bot mode vs user mode

- **Bot mode** uses a bot token (`TELEGRAM_BOT_TOKEN`) and the Bot API. Contacts and some direct-media lookups are unavailable.
- **User mode** uses an MTProto session created by `telegram auth --phone <+number>` and unlocks the `contact` tool and direct media resolution.

## `media(action="download")` fails in bot mode

The Bot API cannot look up a message's media by `(chat_id, message_id)`. In bot mode, `file_id` is **required** -- take it from a message the bot already received (`message` tool results include it) and pass it to `download`. In user mode `file_id` is optional.

## Credentials or settings not saving

There is no browser form and no tool that sets credentials. They come from environment variables or the local CLI, and the server reads them at startup.

- Run `telegram status` to see what is saved, and `config(action="status")` for what the running server sees. Environment variables win over saved credentials.
- After `telegram auth`, restart the server. With no credentials at all, the stdio server prints the setup hint to stderr and exits with status 1.
- The plugin's PreToolUse hook only looks at the `TELEGRAM_PHONE` and `TELEGRAM_BOT_TOKEN` environment variables. If you authorized with `telegram auth` and the hook still blocks tool calls, set one of them in the plugin or client config as well.
- `telegram auth --phone` is interactive: it needs a terminal to read the OTP and 2FA password.
- `config(action="set")` only changes `message_limit` and `timeout` for the running server.

## Session expired / OTP not received

Re-run `telegram auth --phone <+number>` on the machine that runs the server. The OTP is sent to the Telegram app on one of your devices, not by SMS. For a `multi` HTTP user add `--user <namespace>`.

## HTTP server refuses to start or returns 401

- `auth = "no-auth"` only binds a loopback host; a non-loopback `host` exits with status 2. Use `token` or `multi` for anything else.
- An invalid `~/.telegram/config.toml` or `users.toml` prints one line to stderr and exits with status 2.
- A 401 means the client's `Authorization: Bearer <token>` does not match `token_hash` (or no enabled user in `users.toml`). Mint hashes with `telegram token hash`; the server stores only the hash.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/telegram/setup/).

## Filing a bug

Open an issue on [n24q02m/telegram](https://github.com/n24q02m/telegram) with your OS, server version, transport mode, and the last 50 lines of stderr.
