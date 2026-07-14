# Better Email MCP -- Troubleshooting

Common issues specific to better-email-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `npm`/`npx` will not pick a prerelease unless you pin the exact version:

```sh
npx better-email-mcp@<X.Y.Z-beta.N>
```

Replace `<X.Y.Z-beta.N>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Login / connection refused

Most providers reject your normal account password for IMAP/SMTP. Use an **app-specific password** or OAuth token in `EMAIL_CREDENTIALS`. Double-check the IMAP and SMTP host and port for each account -- a wrong port is the most common cause of a connection timeout.

## Folder not found on `move` / `archive`

Folder names differ per provider (`[Gmail]/All Mail`, `Archive`, `Archives`, ...). `archive` auto-detects the archive folder, but `move` needs an exact `destination`. List the real folder names first:

```
folders(action="list")
```

## Attachment send rejected

`send` accepts at most 10 attachments with a total decoded size of 25 MB. Larger payloads are rejected before sending -- split them across messages or share a link instead.

## Credentials or settings not saving

- In the default remote-relay/HTTP mode, submit credentials through the relay form and verify with `config(action="status")`; reset with `config(action="setup_reset")` if it seems stuck. `cache_clear` also drops the cached OAuth token.
- Under stdio there is no browser relay form -- `config__open_relay` returns `stdio_unsupported`. Provide `EMAIL_CREDENTIALS` as an environment variable or `userConfig` field.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/better-email-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/better-email-mcp](https://github.com/n24q02m/better-email-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.
