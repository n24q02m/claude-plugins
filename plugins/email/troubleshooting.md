# Email MCP -- Troubleshooting

Common issues specific to better-email-mcp. For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `npm`/`npx` will not pick a prerelease unless you pin the exact version:

```sh
npx better-email-mcp@<X.Y.Z-beta.N>
```

Replace `<X.Y.Z-beta.N>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Login / connection refused

Most providers reject your normal account password for IMAP/SMTP. Use an **app-specific password** in `EMAIL_CREDENTIALS`, or sign Outlook accounts in with `email auth outlook <address>`. Double-check the IMAP and SMTP host and port for each account -- a wrong port is the most common cause of a connection timeout.

## Folder not found on `move` / `archive`

Folder names differ per provider (`[Gmail]/All Mail`, `Archive`, `Archives`, ...). `archive` auto-detects the archive folder, but `move` needs an exact `destination`. List the real folder names first:

```
folders(action="list")
```

## Attachment rejected when sending

The `messages` actions `new`, `reply`, and `forward` accept at most 10 attachments with a total decoded size of 25 MB. Larger payloads are rejected before sending -- split them across messages or share a link instead.

## Credentials or settings not saving

There is no browser setup form and no runtime credential editor: credentials are read from the server environment (or saved Outlook tokens) when the server starts.

- Check the state with `config(action="status")`. `awaiting_setup` means no credentials were found; `config(action="setup_start")` returns the exact steps.
- Set `EMAIL_CREDENTIALS` (or `EMAIL_USER` + `EMAIL_APP_PASSWORD`) in the plugin's `userConfig` or the client's `env` block, then restart the server; `config(action="setup_complete")` re-checks the state afterwards.
- `config(action="setup_reset")` deletes saved config and returns to `awaiting_setup`; `cache_clear` also drops the cached OAuth token.
- `config(action="set")` always returns `ok: false` -- email has no runtime settings to change.

## Outlook sign-in

Run `email auth outlook <address>` (for example `npx @n24q02m/email auth outlook <address>`), open the Microsoft URL it prints, and enter the code. Tokens are saved to `~/.better-email-mcp/tokens.json`; `email logout [<address>]` removes them. A work or school (Microsoft 365) mailbox also needs `OUTLOOK_TENANT` and `OUTLOOK_EXTRA_DOMAINS`, see [setup](/servers/email/setup/).

## HTTP server refuses to start or returns 401

- Bound to a non-loopback host (a container, or `HOST=0.0.0.0`), the server requires `EMAIL_MCP_TOKEN_HASH` and exits without it. Mint it with `printf '%s' "$TOKEN" | email token hash`.
- A 401 means the client's `Authorization: Bearer <token>` does not match the stored hash. The client sends the raw token; only the hash is stored on the server.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/email/setup/).

## Filing a bug

Open an issue on [n24q02m/email](https://github.com/n24q02m/email) with your OS, server version, transport mode, and the last 50 lines of stderr.
