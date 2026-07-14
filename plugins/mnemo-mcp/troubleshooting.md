# Mnemo MCP -- Troubleshooting

Common issues specific to mnemo-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx mnemo-mcp@<X.Y.0bN>
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## First run is slow

On first start the server downloads a local embedding model. Pre-download it instead of waiting on the first `search_memory` call:

```
config(action="warmup")
```

## Search returns nothing

- Confirm memories exist with `memory_stats` or `list_memories` -- a fresh store is empty.
- `search_memory` is semantic; if you expect an exact-name match, try `memory(action="entity_search")`.
- The `as_of` parameter is only valid with `memory(action="as_of")`; passing it to `search`/`list` returns an error rather than silently ignoring it.

## Sync / passport errors

Passport actions (`sync_now`, `export_passport`, `import_passport`) require `SYNC_PASSPHRASE` to be set. Without it the server cannot encrypt or decrypt the bundle. Trigger a plain Google Drive sync with `config(action="sync")` if you only need cloud backup.

## Credentials or settings not saving

- Under stdio (the default plugin install), there is no browser relay form -- `config__open_relay` returns `stdio_unsupported`. Set provider keys as environment variables or `userConfig` fields instead.
- In HTTP self-host mode, check state with `config(action="setup_status")` and reset with `config(action="setup_reset")` if it seems stuck to an old session.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint** (command string or URL), not by name. Installing the plugin *and* adding a Docker or HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/mnemo-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.
