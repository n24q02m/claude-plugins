# WET (Web Extended Toolkit) -- Manual Setup Guide

wet is a self-hosted web search, extraction, and library-docs server. It speaks **Streamable HTTP only** on a single `/mcp` endpoint -- there is no stdio transport and no hosted public instance. You run one instance (locally or on a host you control) and point MCP clients at it.

The repo is `n24q02m/wet`; the PyPI package is `wet-mcp` and ships the `wet` command (also installed as `wet-mcp`). `wet` is both the control plane and one thin client:

- `wet server start|stop|status` -- run the HTTP server (detached by default, `--foreground` to block).
- `wet config init|path|show|get|set` -- manage `~/.wet/config.toml`.
- `wet token hash <token>` -- print the `scrypt$...` hash for `auth = "token"`.
- `wet users path` -- locate the user store used by `auth = "multi"`.
- `wet docs reindex <library>|import|reembed` -- maintain the docs store; no running server needed.
- `wet search <query>` -- search through the running server.
- `wet warmup` -- probe the configured providers.

## Method overview

| Method | What runs where | Best for |
|---|---|---|
| **1. Plugin + running instance** | Claude Code plugin (skill) connects to your instance via `WET_URL` | Claude Code users who want the plugin |
| **2. Local server + `claude mcp add`** | `wet server start` on your machine | Any MCP client, no plugin |
| **3. docker compose (token auth)** | Always-on container, published on loopback | One instance shared across sessions and clients |
| **4. Remote host** | Your instance behind a TLS proxy at `https://<your-host>/mcp` | Multi-device, claude.ai web, team use |

Every method needs a running instance -- Method 1 only changes how Claude Code connects to it.

> **Pick one registration per client.** Claude Code matches MCP servers by **endpoint** (URL), not by name. If you install the plugin (Method 1) *and* `claude mcp add` an entry for the same instance, both load and `/mcp` shows duplicates. With the plugin installed, set `WET_URL` instead of adding a manual entry.

## Prerequisites

- **Python 3.13** (3.14+ is not supported) and [`uv`](https://docs.astral.sh/uv/getting-started/installation/), for Methods 1, 2, and 4
- Docker with Compose, for Method 3

## Start an instance

### Dev: `uvx` (no-auth, loopback only)

```bash
uvx --python 3.13 --from wet-mcp wet server start --foreground
# MCP endpoint: http://127.0.0.1:8000/mcp
```

Without `--foreground` the server detaches; check it with `wet server status` and stop it with `wet server stop`. With no config file the server binds `127.0.0.1:8000` with `auth = "no-auth"`. `no-auth` refuses any non-loopback bind, so this instance is localhost-only by construction. Override the bind with `--host` / `--port` or `WET_HOST` / `WET_PORT`. Several instances can run side by side on different ports.

To write a real config to edit:

```bash
uvx --python 3.13 --from wet-mcp wet config init   # writes ~/.wet/config.toml; --force overwrites
```

> **Search under `uvx`.** A server running from a `uvx` tool environment cannot auto-start the embedded SearXNG. Without a backend that works there, `search`, `research`, `docs`, and `similar` return an error. Set `SEARCH_BACKENDS` to a keyed provider or to the credential-free `duckduckgo,startpage`, or point `SEARXNG_URL` at an external SearXNG (see "Search backends").

### Always-on: docker compose

Public container images are not published; build from source. In a clone of `n24q02m/wet`:

```bash
cp docker-config/config.example.toml docker-config/config.toml   # then edit, see "Instance config"
docker compose up --build -d
# MCP endpoint: http://127.0.0.1:8000/mcp   (change the host port with WET_PORT=9000)
```

`docker-compose.yml` publishes only on `127.0.0.1`, keeps state in the `wet-data` and `wet-home` volumes, and mounts `docker-config/config.toml` read-only. Inside the container the server binds `0.0.0.0`, so the config **must** use `auth = "token"` or `"multi"` -- `no-auth` refuses that bind.

## Instance config (`~/.wet/config.toml`)

All auth and provider settings live in this host-owned file. MCP clients never see it.

### `[server]` -- bind and auth

| Key | Meaning |
|---|---|
| `host`, `port` | Bind address. `WET_HOST` / `WET_PORT` override them. |
| `auth` | `no-auth` (loopback only), `token` (one shared Bearer token), or `multi` (per-user tokens and namespaces via the users file) |
| `token_hash` | `scrypt$...` hash of the shared token. There is no plaintext token field. |
| `users_file` | User store for `auth = "multi"`; default `~/.wet/users.toml` (`wet users path` prints it) |
| `rpm` | Optional rate limit for shared mode |

| `auth` | Bind allowed | Who can read the data |
|---|---|---|
| `no-auth` (default) | loopback only | Only your OS user |
| `token` | any | Anyone holding the shared token |
| `multi` | any | Each token holder gets a separate namespace under `~/.wet/subs/<sub>/` |

### Token setup (`auth = "token"`)

```bash
openssl rand -hex 32                                              # 1. mint a token
uvx --python 3.13 --from wet-mcp wet token hash <token>           # 2. print the scrypt$ hash
```

3. Paste the printed `scrypt$...` value into `token_hash` and restart the server.
4. Give clients the **plaintext** token; they send it as `Authorization: Bearer <token>`. Do not write the plaintext token into any file you commit.

### `[models.*]` -- provider cells

Each task has its own independent cell with `base_url`, `api_key`, and `model`, spoken over OpenAI-compatible HTTP:

| Cell | Used for |
|---|---|
| `[models.embed]` | Embedding vectors for the docs index |
| `[models.rerank]` | Cross-encoder reranking of docs results |
| `[models.chat]` | LLM features: `expand`, `extract_structured`, `extract(action="agent")`, and the `similar` fallback |
| `[models.jev_score]` | LLM-based scoring |

- OpenRouter is pre-wired as the default `base_url`. Any OpenAI-compatible endpoint works, cloud or local, and the cells can be mixed. Choose the models yourself.
- `api_key` may be left empty in the file and supplied by env instead: `HULL_EMBED_API_KEY`, `HULL_RERANK_API_KEY`, `HULL_CHAT_API_KEY`, `HULL_JEV_SCORE_API_KEY`. These are host-only and win over the file. `OPENROUTER_API_KEY` serves every cell that keeps the default OpenRouter `base_url`, and also the `openrouter` search backend.
- With no `embed`/`rerank` key, wet falls back to local ONNX models (downloaded on first use). With no `[models.chat]` key, the LLM-backed features are off.

### Changing the embedding model

Vectors from one embedding model cannot be searched with another, and the server refuses to boot after the model changes. Start it once with `REINDEX_ON_MODEL_CHANGE=true` to rebuild, then run `wet docs reembed` for any entry still missing a vector.

## Search backends

`SEARCH_BACKENDS` is an ordered, comma-separated fallback chain read by the server:

| Backend | Needs |
|---|---|
| `searxng` | Embedded SearXNG (auto-started outside `uvx`) or an external `SEARXNG_URL` |
| `tavily` | `TAVILY_API_KEY` |
| `brave` | `BRAVE_API_KEY` |
| `exa` | `EXA_API_KEY` |
| `kagi` | `KAGI_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` (plus `OPENROUTER_MODEL`, optionally `OPENROUTER_BASE_URL`, `OPENROUTER_SEARCH_ENGINE`) |
| `firecrawl` | `FIRECRAWL_API_KEY` optional; keyless attempts are made when absent |
| `duckduckgo`, `startpage` | Nothing; credential-free. Datacenter IPs may hit bot challenges, and the chain then advances to the next backend. |

Every search response includes a `search_backend` trace: requested, attempted, selected, and a `fallback` state (`none`, `used`, `exhausted`, or `unavailable`).

## Browser backends

`BROWSER_BACKENDS` is an ordered list that selects how pages are rendered when extraction escalates: `native` (default when empty), `browserless` (`BROWSERLESS_URL`, `BROWSERLESS_TOKEN`), and `invisible` (`STEALTHFOX_BINARY`, optional `CAPSOLVER_API_KEY`). It does not route `extract(action="interact")`, which always uses native Patchright sessions.

## Method 1: Claude Code plugin

The plugin installs the wet skill and registers an HTTP MCP entry pointing at your instance.

1. Start an instance (see above) and note its endpoint.
2. Install the plugin:
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install wet@n24q02m-plugins
   ```
3. Answer the install prompts (stored by Claude Code; sensitive values go to the system keychain and persist across `/plugin update`):

   | Field | Required | Value |
   |---|---|---|
   | `WET_URL` | Optional | Streamable HTTP endpoint of your instance, e.g. `http://127.0.0.1:8000/mcp` |
   | `WET_TOKEN` | Optional | The plaintext token for `auth = "token"` / `"multi"`; leave empty for a loopback `no-auth` instance |

   Without `WET_URL` the skill still installs, but the MCP entry has no endpoint and its tools do not connect.
4. Restart Claude Code and check `/mcp`.

## Method 2: local server + `claude mcp add`

```bash
uvx --python 3.13 --from wet-mcp wet server start
claude mcp add --transport http wet http://127.0.0.1:8000/mcp
```

For a token-auth instance, add `--header "Authorization: Bearer <token>"`. Other clients (Codex, Gemini CLI, Cursor, Windsurf) register the same URL in their MCP settings:

```json
{
  "mcpServers": {
    "wet": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

Drop `headers` for a `no-auth` instance.

## Method 3: docker compose

Start the compose stack (see "Always-on" above), then register `http://127.0.0.1:8000/mcp` with the Bearer header -- through the plugin's `WET_URL` / `WET_TOKEN`, or with `claude mcp add` as in Method 2.

## Method 4: remote host

Run the instance on a reachable host with `auth = "token"` or `"multi"`, and front it with a TLS proxy of your choice (the server itself serves plain HTTP). Clients use `https://<your-host>/mcp`:

```bash
claude mcp add --transport http wet https://<your-host>/mcp --header "Authorization: Bearer <token>"
```

claude.ai web and other remote clients connect the same way.

## Backup and migration

Server state lives under `~/.wet/` (in the `wet-home` and `wet-data` volumes for compose): `config.toml`, the SQLite (WAL) docs index `docs.db`, the web cache, and downloads. The server has no embedded sync; back up or move the directory with `rclone` or any file tool while the server is stopped. `wet docs import` loads a Cloudflare D1 SQL export into `docs.db`.

## Environment variables

Most settings live in `config.toml`. The server host also reads:

| Variable | Default | Description |
|---|---|---|
| `WET_HOST` / `WET_PORT` | from `[server]` | Override the bind address |
| `HULL_EMBED_API_KEY` / `HULL_RERANK_API_KEY` / `HULL_CHAT_API_KEY` / `HULL_JEV_SCORE_API_KEY` | -- | `api_key` for the matching `[models.*]` cell |
| `OPENROUTER_API_KEY` | -- | Default credential for OpenRouter cells and the `openrouter` search backend |
| `SEARCH_BACKENDS` | -- | Ordered search fallback chain |
| `TAVILY_API_KEY`, `BRAVE_API_KEY`, `EXA_API_KEY`, `KAGI_API_KEY`, `FIRECRAWL_API_KEY` | -- | Keys for the matching search backends |
| `WET_AUTO_SEARXNG` | `true` | Auto-start embedded SearXNG (not possible under `uvx`) |
| `SEARXNG_URL` | `http://localhost:41592` | External SearXNG instance |
| `WET_SEARXNG_PORT` | `41592` | Port of the embedded SearXNG |
| `SEARXNG_AUTH_USER` / `SEARXNG_AUTH_PASS` | -- | Basic auth for an external SearXNG |
| `DISABLE_LOCAL_SEARCH` / `DISABLE_LOCAL_BROWSER` / `DISABLE_LOCAL_EMBED` / `DISABLE_LOCAL_RERANK` | `false` | Turn off the matching local resource |
| `WET_SEARCH_BUDGET` | `0` | Per-provider attempt budget per process (`0` = unlimited) |
| `BROWSER_BACKENDS` | -- (native) | Page renderer chain: `native`, `browserless`, `invisible` |
| `BROWSERLESS_URL` / `BROWSERLESS_TOKEN` | -- | Browserless endpoint and token |
| `STEALTHFOX_BINARY` / `CAPSOLVER_API_KEY` | -- | `invisible` backend binary and optional CAPTCHA solver key |
| `RESPECT_ROBOTS_TXT` | `false` | Honor `robots.txt` when fetching |
| `WET_CACHE` | `true` | Web cache for search, extract, and diff |
| `CACHE_DIR` | `~/.wet` | Cache and state directory |
| `DOCS_DB_PATH` | `~/.wet/docs.db` | Docs index location |
| `DOWNLOAD_DIR` | `~/.wet/downloads` | Where `media(action="download")` may write |
| `TOOL_TIMEOUT` | `120` | Per-call timeout in seconds |
| `RERANK_ENABLED` | `true` | Toggle reranking |
| `RERANK_TOP_N` | `10` | Results kept after reranking |
| `LOCAL_EMBEDDING_MODEL` / `LOCAL_RERANK_MODEL` | -- | Local ONNX model overrides |
| `REINDEX_ON_MODEL_CHANGE` | `false` | One-shot vector rebuild after changing the embedding model |
| `CONVERT_ALLOWED_DIRS` | -- | Comma-separated directories `extract(action="convert")` may read. Empty means the server's working directory and temp directory. |
| `CONVERT_MAX_FILE_SIZE` | 100 MB | Largest file `convert` accepts |
| `GITHUB_TOKEN` / `GH_TOKEN` | from `gh auth token` | Raises the GitHub rate limit for docs discovery (60 to 5000 requests per hour) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Troubleshooting

See the [troubleshooting page](/servers/wet/troubleshooting/).
