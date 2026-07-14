# Better Notion MCP -- Troubleshooting

Common issues specific to better-notion-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `npm`/`npx` will not pick a prerelease unless you pin the exact version:

```sh
npx better-notion-mcp@<X.Y.Z-beta.N>
```

Replace `<X.Y.Z-beta.N>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Tools return empty results or "not found"

A Notion integration only sees pages and databases that have been **shared with it**. If searches come back empty or a known page 404s, open the page in Notion, choose *Connections*, and add your integration. Confirm the token is loaded with `config(action="status")`.

## 429 / rate-limited

Notion allows roughly 3 requests/second per integration. The composite tools batch where possible, but tight loops still hit the limit; the upstream 429 is surfaced in the tool result. Space out bulk operations.

## Re-authorize loop on remote-oauth

Every tool call returning 401 usually means the JWT `sub` is changing between calls, so credentials scope to a new subject each time. Authenticate once and stay logged in, or re-submit credentials under the current subject. See the [multi-user pattern](/reference/multi-user-pattern/).

## Credentials or settings not saving

- In the default remote-oauth/HTTP mode, submit the token through the relay form and verify with `config(action="status")`; reset with `config(action="setup_reset")` if it seems stuck.
- Under stdio there is no browser relay form -- `config__open_relay` returns `stdio_unsupported`. Set `NOTION_TOKEN` as an environment variable or `userConfig` field.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/better-notion-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.
