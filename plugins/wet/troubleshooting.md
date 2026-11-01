# WET (Web Extended Toolkit) -- Troubleshooting

Common issues specific to wet. For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx --python 3.13 --from wet-mcp==<X.Y.0bN> wet server start
```

Replace `<X.Y.0bN>` with the exact beta version (for example, the value shown on the package's release history). Drop the version pin to return to the latest stable.

## Server fails to start on Python 3.14+

wet requires **Python 3.13**. Always pin the interpreter:

```sh
uvx --python 3.13 --from wet-mcp wet server start
```

## Connection refused / no tools in `/mcp`

wet has no stdio mode: the client must reach a running HTTP instance. Check it:

```sh
wet server status
```

It reports the pid, the lock, and HTTP liveness for the configured port. If HTTP is down, run `wet server start` (or `--foreground` to see errors). Then check that the URL given to `claude mcp add` ends in `/mcp` and uses the same port as `[server].port` (default 8000). `wet search <query>` is a quick end-to-end check; it exits with code 2 and a hint when no server is running.

## 401 Unauthorized

The server stores only `token_hash`; clients must send the **plaintext** token as `Authorization: Bearer <token>`. A `scrypt$...` hash in the client config is wrong. Regenerate the hash with `wet token hash <token>` if you are unsure which token the server holds.

## Server refuses to bind (no-auth)

`auth = "no-auth"` is loopback-only and refuses any other bind address. For a container or a reachable host, set `auth = "token"` or `"multi"` in `~/.wet/config.toml`.

## First run is slow / downloads a lot

Downloads depend on the selected backends. Local embedding/reranker models and a native browser may need initial downloads. Prepare the enabled local resources in advance with:

```
wet warmup
```

or `config(action="warmup")` from a connected client.

## Search returns an error or no results

- Under `uvx`, local SearXNG cannot auto-start. If no backend that can run there is configured, `search`, `research`, `docs`, and `similar` return an error. Set `SEARCH_BACKENDS` on the server host to a keyed provider or to `duckduckgo,startpage`, or point `SEARXNG_URL` at an external SearXNG.
- Read the `search_backend` trace in the response: it shows which backends were requested and attempted and whether the chain fell back or was exhausted.
- `duckduckgo` and `startpage` can hit bot challenges from datacenter IPs; the chain advances to the next backend.

## SearXNG port conflict

If the embedded SearXNG port 41592 is already in use, move it on the server host:

```sh
export WET_SEARXNG_PORT=<alternate-port>
```

## Embedding model mismatch / server refuses to boot

Changing the `[models.embed]` model makes existing vectors unusable, and the server refuses to boot until they are rebuilt. Start it once with `REINDEX_ON_MODEL_CHANGE=true`, then run `wet docs reembed` to backfill any entry still missing a vector.

## LLM-backed features return an error or are disabled

`expand`, `extract_structured`, `extract(action="agent")`, and the `similar` fallback need a working `[models.chat]` cell. Set its `api_key` in `~/.wet/config.toml` or through `HULL_CHAT_API_KEY` (or `OPENROUTER_API_KEY` for the default OpenRouter `base_url`) on the server host, then restart.

## `convert` rejects a path

`extract(action="convert")` only reads files inside the allowed directories: by default the server's working directory and temp directory. Use an absolute path inside one of them, or list the directory in `CONVERT_ALLOWED_DIRS` (comma-separated) on the server host.

## Library docs lookups are rate limited

Docs discovery calls the GitHub API, limited to 60 requests per hour without a token. wet reads a token from `GITHUB_TOKEN` / `GH_TOKEN` or from `gh auth token` on the server host, which raises the limit to 5000 per hour.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint** (URL), not by name. Do not register the same instance twice with `claude mcp add`. The `plugin:wet:wet` entry shown as failed is the plugin's bundled stdio entry: wet 3.20.0 is HTTP-only and the `wet-mcp` entry point prints its CLI usage and exits, so it cannot connect. Use your manual HTTP entry and ignore it. See [setup](/servers/wet/setup/) for the full method matrix.

## Filing a bug

Open an issue on [n24q02m/wet](https://github.com/n24q02m/wet) with your OS, server version (`wet -V`), auth mode, and the last 50 lines of the server log.
