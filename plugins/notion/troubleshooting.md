# Notion MCP -- Troubleshooting

Common issues specific to better-notion-mcp. For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `npm`/`npx` will not pick a prerelease unless you pin the exact version:

```sh
npx @n24q02m/notion@<X.Y.Z-beta.N>
```

Replace `<X.Y.Z-beta.N>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Tools return empty results or "not found"

A Notion integration only sees pages and databases that have been **shared with it**. If searches come back empty or a known page 404s, open the page in Notion, choose *Connections*, and add your integration. Confirm the token is loaded with `config(action="status")`.

## 429 / rate-limited

Notion allows roughly 3 requests/second per integration. The composite tools batch where possible, but tight loops still hit the limit; the upstream 429 is surfaced in the tool result. Space out bulk operations.

## Tool result tells you to run `notion auth`

The server has no Notion token for your user. Provide one in either way:

- Set `NOTION_TOKEN` (plugin `userConfig` field or environment variable), or
- Run `npx -y @n24q02m/notion auth` on the machine that runs the server. It reads the token from `NOTION_TOKEN` or prompts for it, verifies it with Notion, and stores it under `~/.better-notion/`.

In HTTP `multi` mode each user needs their own token: `notion auth --user <namespace>` on the server host. Then check with `config(action="status")`; it reports `state`, `has_token`, and `token_source` (`environment` or `config`).

In stdio mode the server exits at startup with an error on stderr when neither a `NOTION_TOKEN` nor a stored token exists.

## 401 from the HTTP endpoint

A 401 on `/mcp` means the bearer token is missing or wrong, not that Notion rejected anything. Send `Authorization: Bearer <your-token>` and check it against the server's auth mode: in `multi` mode the token must belong to a user in `MCP_USERS_FILE`; in `token` mode it must match the token behind `MCP_AUTH_TOKEN_HASH`.

A 401 inside a tool result (for example "Could not find integration") comes from Notion: the stored integration token is invalid or was revoked at https://www.notion.so/my-integrations.

## Replacing a stored token

`config(action="setup_reset", force=true)` clears the token saved on the server host (it refuses without `force`). Then store a new one with `notion auth`. A token supplied through `NOTION_TOKEN` is not stored by the server, so change that variable instead.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/notion/setup/).

## Filing a bug

Open an issue on [n24q02m/notion](https://github.com/n24q02m/notion) with your OS, server version, transport mode, and the last 50 lines of stderr.
