# Better Code Review Graph -- Troubleshooting

Common issues specific to better-code-review-graph (crg). For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx n24q02m-crg@<X.Y.0bN>
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Query or review returns nothing

The graph is built on demand -- run a build before querying:

```
graph(action="build")
```

`review(action="context")` and `query(action="impact")` need a populated graph; on an empty graph they return no impacted nodes.

## Embeddings unavailable

Vector search uses local Fastretrieval embeddings when `EMBEDDING_MODELS` is empty and the local leg is enabled (`DISABLE_LOCAL_EMBED` unset). With `DISABLE_LOCAL_EMBED` set and no cloud entry, embedding reports `unavailable`.

Cloud embeddings need an explicit `EMBEDDING_MODELS` entry **and** a `[models.embed]` cell with a key (in `config.toml`, or via `HULL_EMBED_API_KEY`). A key alone does not select a model, and vendor-specific key variables such as `OPENAI_API_KEY` are not read.

Node summaries need a configured `[models.chat]` cell (key in `config.toml` or `HULL_CHAT_API_KEY`). Without one, `graph(action="summarize")` returns `status: skipped` with `reason: no_provider_configured`. There is no local-summary fallback.

For Cohere `embed-v4.0`, stored and returned vectors must be exactly 1024 dimensions. Re-run `graph(action="embed")` for an old 768-wide index instead of slicing or padding results. If the graph disappeared after an upgrade, rebuild it with `graph(action="build", full_rebuild=true)` in the `.crg/` state directory, then embed. Older `.better-code-review-graph/` and `.code-review-graph/` state is not automatically adopted or removed.

## Security scan finds nothing / wrong engine

`security(action="scan")` defaults to the `heuristic` engine. For deeper rules, pass `engine="semgrep"` (Semgrep must be installed). Use `security(action="rule_list")` to see active rules and `suppress` to mute a noisy one.

## Model keys or settings not applying

- crg takes no keys from clients. Keys are host-owned: put them in the `[models.<task>]` cells of `~/.crg/config.toml` (or `$CRG_CONFIG_DIR/config.toml`), or set `HULL_EMBED_API_KEY` / `HULL_CHAT_API_KEY`. With the plugin, enter them in the install prompts.
- Print the config path and contents with `crg config path` and `crg config show`.
- Check state with `config(action="setup_status")`, which reports the configured model cells under `providers_configured`. `config(action="setup_start")` explains where the host configures keys. If the state seems stuck, `config(action="setup_reset")` returns to local mode and `config(action="setup_complete")` re-resolves it from the host config.
- `config(action="set")` only changes `log_level` at runtime.

## HTTP instance: connection refused, 401, or refuses to start

- The server exposes `/mcp`. Check the instance is up: `crg server start` defaults to `http://127.0.0.1:8000/mcp`, the compose stack to `http://127.0.0.1:8772/mcp`.
- A 401 means the Bearer token the client sends does not match `token_hash` in `config.toml`. Clients send the plaintext token; the file stores only the `scrypt$...` hash. To replace a lost token, mint a new one, run `crg token hash <token>`, paste the hash into `token_hash`, and restart.
- `auth = "no-auth"` only binds loopback. In the compose container, which binds `0.0.0.0`, set `auth = "token"` or `"multi"`.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a manual stdio or HTTP entry loads both. Pick one method and uninstall the other. See [setup](/servers/crg/setup/).

## Filing a bug

Open an issue on [n24q02m/crg](https://github.com/n24q02m/crg) with your OS, server version, transport mode, and the last 50 lines of stderr.
