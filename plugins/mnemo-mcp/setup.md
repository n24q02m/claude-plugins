# Mnemo MCP -- Manual Setup Guide

mnemo is a self-hosted memory server. It speaks **Streamable HTTP only** on a single `/mcp` endpoint -- there is no stdio transport and no hosted public instance. You run one instance (locally or on a host you control) and point MCP clients at it.

The repo is `n24q02m/mnemo`; the PyPI package is `mnemo-mcp` and ships two commands:

- `mnemo-mcp` -- a bare invocation starts the HTTP server; the subcommands `config-init`, `warmup`, `token-hash`, and `token-verify` run one operator action and exit.
- `mnemo` -- a CLI over the memory database (`capture`, `recall`, `reflect`, `fetch`, `standing-*`, each taking `--db <path>`). It never starts a server.

## Method overview

| Method | What runs where | Best for |
|---|---|---|
| **1. Plugin + running instance** | Claude Code plugin (skills + hooks) connects to your instance via `MNEMO_URL` | Claude Code users who want the skills and hooks |
| **2. Local server + `claude mcp add`** | `uvx --from mnemo-mcp mnemo-mcp` on your machine | Any MCP client, no plugin |
| **3. docker compose (token auth)** | Always-on container, published on loopback | One instance shared across sessions and clients |
| **4. Remote host** | Your instance behind a TLS proxy at `https://<your-host>/mcp` | Multi-device, claude.ai web, team use |

Every method needs a running instance -- Method 1 only changes how Claude Code connects to it.

> **Pick one registration per client.** Claude Code matches MCP servers by **endpoint** (URL), not by name. If you install the plugin (Method 1) *and* `claude mcp add` an entry for the same instance, both load and `/mcp` shows duplicates. With the plugin installed, set `MNEMO_URL` instead of adding a manual entry.

## Prerequisites

- **Python 3.13** (3.14+ is not supported) and [`uv`](https://docs.astral.sh/uv/getting-started/installation/), for Methods 1, 2, and 4
- Docker with Compose, for Method 3

## Start an instance

### Dev: `uvx` (no-auth, loopback only)

```bash
uvx --from mnemo-mcp mnemo-mcp
# MCP endpoint: http://127.0.0.1:8000/mcp
```

With no config file the server binds `127.0.0.1:8000` with `auth = "no-auth"`. `no-auth` refuses any non-loopback bind, so this instance is localhost-only by construction. Override the bind with `MNEMO_HOST` / `MNEMO_PORT`.

To write a real config to edit:

```bash
uvx --from mnemo-mcp mnemo-mcp config-init   # writes ~/.mnemo/config.toml; --force overwrites
```

### Always-on: docker compose

Public container images are no longer published; build from source. In a clone of `n24q02m/mnemo`:

```bash
cp mnemo-config/config.example.toml mnemo-config/config.toml   # then edit, see "Instance config"
docker compose -f docker-compose.http.yml up --build -d
# MCP endpoint: http://127.0.0.1:8771/mcp   (change the host port with MNEMO_PORT=9000)
```

`docker-compose.http.yml` publishes only on `127.0.0.1`, keeps all state in the `mnemo-data` volume, and mounts `mnemo-config/config.toml` read-only. Inside the container the server binds `0.0.0.0`, so the config **must** use `auth = "token"` or `"multi"` -- `no-auth` refuses that bind. For `auth = "multi"`, also mount `users.toml` (the commented line in the compose file).

To build the image without Compose: `docker build --target http .`

## Instance config (`~/.mnemo/config.toml`)

All auth and provider settings live in this host-owned file. MCP clients never see it.

### `[server]` -- bind and auth

| Key | Meaning |
|---|---|
| `host`, `port` | Bind address. `MNEMO_HOST` / `MNEMO_PORT` override them. |
| `auth` | `no-auth` (loopback only), `token` (one shared Bearer token), or `multi` (per-user tokens and namespaces via `users.toml`) |
| `token_hash` | `scrypt$...` hash of the shared token. There is no plaintext token field. |
| `rpm` | Optional rate limit for shared mode |

| `auth` | Bind allowed | Storage | Who can read the data |
|---|---|---|---|
| `no-auth` (default) | loopback only | `~/.mnemo/memories.db` | Only your OS user |
| `token` | any | same, one shared namespace | Anyone holding the shared token |
| `multi` | any | per-namespace `~/.mnemo/subs/<ns>/memories.db` | Each token holder sees only their own namespace |

### Token setup (`auth = "token"`)

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"   # 1. mint a token
MNEMO_AUTH_TOKEN=<token> uvx --from mnemo-mcp mnemo-mcp token-hash   # 2. print the scrypt$ hash
```

3. Paste the printed `scrypt$...` value into `token_hash` and restart the server.
4. Give clients the **plaintext** token; they send it as `Authorization: Bearer <token>`. In a source checkout, `uv run mnemo-mcp token-hash` works the same way.

`mnemo-mcp token-verify <token> <scrypt$...>` checks a token against a stored hash.

### `[models.*]` -- provider cells

Each task has its own independent cell with `base_url`, `api_key`, and `model`, spoken over OpenAI-compatible HTTP:

| Cell | Used for |
|---|---|
| `[models.embed]` | Embedding vectors for semantic search |
| `[models.rerank]` | Cross-encoder reranking of search results |
| `[models.chat]` | LLM features: compression, consolidation, importance scoring |
| `[models.jev_score]` | LLM-based scoring |

- OpenRouter is pre-wired as the default `base_url`. Any OpenAI-compatible endpoint works, cloud or local, and the cells can be mixed (for example a cloud `chat` cell with local `embed`/`rerank`).
- `mnemo-config/config.example.toml` in the repo shows a complete set of example cells. Choose the models yourself; the example values are not a recommendation.
- `api_key` may be left empty in the file and supplied by env instead: `HULL_EMBED_API_KEY`, `HULL_RERANK_API_KEY`, `HULL_CHAT_API_KEY`, `HULL_JEV_SCORE_API_KEY`. These are host-only.
- With no `embed`/`rerank` cell, mnemo falls back to the local Fastretrieval ONNX models (downloaded on first use, ~570 MB). An unconfigured cell never silently selects a paid provider. `consolidate_memories` returns an error naming the missing cell when `[models.chat]` is not configured.

### Changing the embedding model

Vectors from one embedding model cannot be searched with another. After changing the `[models.embed]` model, start the server once with `REINDEX_ON_MODEL_CHANGE=true` to rebuild the vectors, then run `config(action="backfill_embeddings")` for any memory still missing one.

## Method 1: Claude Code plugin

The plugin installs the mnemo skills (`recall-context`, `memory-commit`, `knowledge-audit`, `session-handoff`, `temporal-query`) and hooks, and registers an HTTP MCP entry pointing at your instance.

1. Start an instance (see above) and note its endpoint.
2. Install the plugin:
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install mnemo-mcp@n24q02m-plugins
   ```
3. Answer the install prompts (stored by Claude Code; sensitive values go to the system keychain and persist across `/plugin update`):

   | Field | Required | Value |
   |---|---|---|
   | `MNEMO_URL` | Optional | Streamable HTTP endpoint of your instance, e.g. `http://127.0.0.1:8000/mcp` (uvx) or `http://127.0.0.1:8771/mcp` (compose) |
   | `MNEMO_TOKEN` | Optional | The plaintext token for `auth = "token"` / `"multi"`; leave empty for a loopback `no-auth` instance |

   Without `MNEMO_URL` the skills and hooks still install, but the MCP entry has no endpoint and its tools do not connect.
4. Restart Claude Code and check `/mcp`.

Hooks: a SessionStart hook nudges `recall-context` on every session. The PostToolUse hook that hints `memory-commit` after edits to `CLAUDE.md` / `AGENTS.md` / docs is opt-in via `CAPTURE_AUTO_ENABLED=true`.

## Method 2: local server + `claude mcp add`

```bash
uvx --from mnemo-mcp mnemo-mcp
claude mcp add --transport http mnemo http://127.0.0.1:8000/mcp
```

For a token-auth instance, add `--header "Authorization: Bearer <token>"`. Other clients (Codex, Gemini CLI, Cursor, Windsurf) register the same URL in their MCP settings:

```json
{
  "mcpServers": {
    "mnemo": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

Drop `headers` for a `no-auth` instance.

## Method 3: docker compose

Start the compose stack (see "Always-on" above), then register `http://127.0.0.1:8771/mcp` with the Bearer header -- through the plugin's `MNEMO_URL` / `MNEMO_TOKEN`, or with `claude mcp add` as in Method 2.

## Method 4: remote host

Run the instance on a reachable host with `auth = "token"` or `"multi"`, and front it with a TLS proxy of your choice (the server itself serves plain HTTP). Clients use `https://<your-host>/mcp`:

```bash
claude mcp add --transport http mnemo https://<your-host>/mcp --header "Authorization: Bearer <token>"
```

claude.ai web and other remote clients connect the same way.

## Backup and migration

All state is one SQLite (WAL) database plus `config.toml` under `~/.mnemo/` (under `/data/.mnemo/` in the container). The server has no embedded sync; back up or move the directory with `rclone` or any file tool while the server is stopped, or use `export_memories` / `import_memories`.

## Environment variables

Most settings live in `config.toml`. The server also reads:

| Variable | Default | Description |
|---|---|---|
| `MNEMO_HOST` / `MNEMO_PORT` | from `[server]` | Override the bind address |
| `MNEMO_AUTH_TOKEN` | -- | Token read by `mnemo-mcp token-hash` |
| `HULL_EMBED_API_KEY` / `HULL_RERANK_API_KEY` / `HULL_CHAT_API_KEY` / `HULL_JEV_SCORE_API_KEY` | -- | `api_key` for the matching `[models.*]` cell |
| `DB_PATH` / `MNEMO_DB_PATH` | `~/.mnemo/memories.db` | Database location |
| `REINDEX_ON_MODEL_CHANGE` | `false` | One-shot vector rebuild after changing the embedding model |
| `RERANK_ENABLED` | `true` | Toggle reranking |
| `RERANK_TOP_N` | `10` | Results kept after reranking |
| `DEDUP_THRESHOLD` | `0.9` | Similarity above which a capture is treated as a duplicate |
| `DEDUP_WARN_THRESHOLD` | `0.7` | Similarity above which a capture warns about a near-duplicate |
| `RECENCY_HALF_LIFE_DAYS` | `7` | Half-life for temporal decay in search scoring |
| `ARCHIVE_ENABLED` | `true` | Auto-archive old, low-importance memories |
| `ARCHIVE_AFTER_DAYS` | `90` | Age before a memory is eligible for auto-archive |
| `ARCHIVE_IMPORTANCE_THRESHOLD` | `0.3` | Memories below this importance are auto-archived |
| `ARCHIVE_TRIGGER_EVERY` | `100` | Run the archive sweep every N captures |
| `COMPRESSION_ENABLED` | `true` | LLM compression on capture (needs `[models.chat]`) |
| `KG_AUTO_ENABLED` | `false` | Auto-extract entities into the knowledge graph on capture |
| `LOG_LEVEL` | `INFO` | Logging level |

`CAPTURE_AUTO_ENABLED=true` is read by the plugin's PostToolUse hook, not by the server.

## Troubleshooting

See the [troubleshooting page](/servers/mnemo-mcp/troubleshooting/).
