# Mnemo MCP -- Troubleshooting

Common issues specific to mnemo-mcp. For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx --from mnemo-mcp@<X.Y.0bN> mnemo-mcp
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Tools do not connect / connection refused

mnemo has no stdio transport: a client can only reach a running instance.

- Check the instance is up: a `uvx --from mnemo-mcp mnemo-mcp` process (default `http://127.0.0.1:8000/mcp`) or the compose stack (default `http://127.0.0.1:8771/mcp`).
- With the plugin, `MNEMO_URL` must be set to that endpoint, including the `/mcp` path. Without it the skills and hooks install, but the MCP entry has no endpoint. Re-run `/plugin install` or update the plugin's options to set it.
- A remote instance must be reachable over TLS at `https://<your-host>/mcp`.

## 401 Unauthorized

The Bearer token the client sends does not match the instance's `token_hash`.

- The client sends the **plaintext** token (`MNEMO_TOKEN` for the plugin, or `Authorization: Bearer <token>`); `config.toml` stores only the `scrypt$...` hash.
- Check a token against the stored hash: `mnemo-mcp token-verify <token> <scrypt$...>`.
- To replace a lost token, mint a new one, run `MNEMO_AUTH_TOKEN=<token> mnemo-mcp token-hash`, paste the hash into `token_hash`, and restart the server.

## Server refuses to start on a non-loopback address

`auth = "no-auth"` only binds loopback. Inside the compose container (which binds `0.0.0.0`) or on any published host, set `auth = "token"` or `"multi"` in `config.toml`. See [instance config](/servers/mnemo-mcp/setup/#instance-config-mnemoconfigtoml).

## First run is slow

With no `[models.embed]` cell, the server downloads a local embedding model (~570 MB) on first use. Pre-download it instead of waiting on the first `search_memory` call:

```
config(action="warmup")
```

or, before starting the server, `mnemo-mcp warmup`.

## Search returns nothing

- Confirm memories exist with `memory_stats` or `list_memories` -- a fresh store is empty.
- `search_memory` is semantic; if you expect an exact-name match, try `memory(action="entity_search")`.
- Memories captured while embedding was unavailable have no vector; run `config(action="backfill_embeddings")`.
- The `as_of` parameter is only valid with `memory(action="as_of")`; passing it to `search`/`list` returns an error rather than silently ignoring it.

## Embedding model mismatch after changing `[models.embed]`

Vectors from one embedding model cannot be searched with another, so the server refuses to serve a database built with a different model. Start it once with `REINDEX_ON_MODEL_CHANGE=true` to rebuild the vectors (with compose: `REINDEX_ON_MODEL_CHANGE=true docker compose -f docker-compose.http.yml up`), then run `config(action="backfill_embeddings")`.

## Consolidation fails

`consolidate_memories` needs a `[models.chat]` cell in `config.toml`; without one it returns an error naming the missing cell.

## Duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint** (URL), not by name. Installing the plugin *and* adding a manual `claude mcp add` entry for the same instance loads both. Pick one registration and remove the other. See [setup](/servers/mnemo-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/mnemo](https://github.com/n24q02m/mnemo) with your OS, server version, `auth` mode, how you run the instance (uvx, compose, remote), and the last 50 lines of the server log.
