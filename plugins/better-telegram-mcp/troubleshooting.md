# Better Telegram MCP -- Troubleshooting

Common issues specific to better-telegram-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx better-telegram-mcp@<X.Y.0bN>
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Bot mode vs user mode

- **Bot mode** uses a bot token (`TELEGRAM_BOT_TOKEN`) and the Bot API. Contacts and some direct-media lookups are unavailable.
- **User mode** uses an MTProto session authenticated through the relay form and unlocks the `contact` tool and direct media resolution.

## `media(action="download")` fails in bot mode

The Bot API cannot look up a message's media by `(chat_id, message_id)`. In bot mode, `file_id` is **required** -- take it from a message the bot already received (`message` tool results include it) and pass it to `download`. In user mode `file_id` is optional.

## Credentials or settings not saving

- Under stdio there is no browser relay form -- `config__open_relay` returns `stdio_unsupported`. Set the bot token as an environment variable or `userConfig` field.
- In remote-relay/HTTP mode, check `config(action="setup_status")` and reset with `config(action="setup_reset")` if it seems stuck to an old session. User-mode MTProto sessions are re-authenticated through the relay form.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/better-telegram-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.
