# WET (Web Extended Toolkit) -- Manual Setup Guide

wet is a self-hosted web search, extraction, and library-docs server. It speaks **Streamable HTTP only** on a single `/mcp` endpoint -- there is no stdio transport and no hosted public instance. You run one instance (locally or on a host you control) and point MCP clients at it.

The repo is `n24q02m/wet`; the PyPI package is `n24q02m-wet` and installs three console scripts: `n24q02m-wet` (primary package command), `wet` (short alias), and `wet-mcp` (legacy alias for `uvx wet-mcp` configs; the separate `wet-mcp` PyPI package is a transitional stub that installs `n24q02m-wet`). `wet` is both the control plane and one thin client; a bare invocation prints its usage:

- `wet server start|stop|status` -- run the HTTP server (detached by default, `--foreground` to block).
- `wet config init|path|show|get|set` -- manage `~/.wet/config.toml`.
- `wet token hash` -- print the `scrypt$...` hash for `auth = "token"` (reads the token from stdin or a hidden prompt, never from the command line).
- `wet users path` -- locate the user store used by `auth = "multi"`.
- `wet docs list|reindex <library>|import|reembed` -- maintain the docs store; no running server needed.
- `wet search <query>` -- search through the running server.
- `wet warmup` -- run first-run setup, probe the cloud model cells, and pre-download local models when no cloud cell is ready.

## Method overview

| Method | What runs where | Best for |
|---|---|---|
| **1. Plugin (skills + HTTP entry)** | Claude Code plugin installs six skills, a SessionStart hook, and an HTTP entry pointing at `WET_URL`; you start the instance yourself | Claude Code users who want the skills |
| **2. Local server + `claude mcp add`** | `wet server start` on your machine | Any MCP client, no plugin |
| **3. docker compose (token auth)** | Always-on container, published on loopback | One instance shared across sessions and clients |
| **4. Remote host** | Your instance behind a TLS proxy at `https://<your-host>/mcp` | Multi-device, claude.ai web (conditions below), team use |

Every method needs a running instance.

> **Pick one registration per client.** Claude Code matches MCP servers by **endpoint** (URL), not by name. If you use the plugin (Method 1), do not also run `claude mcp add` for the same URL.

## Prerequisites

- **Python 3.13** (3.14+ is not supported) and [`uv`](https://docs.astral.sh/uv/getting-started/installation/), for Methods 1, 2, and 4
- Docker with Compose, for Method 3

## Start an instance

### Dev: `uvx` (no-auth, loopback only)

```bash
uvx --python 3.13 --from n24q02m-wet wet server start --foreground
# MCP endpoint: http://127.0.0.1:8000/mcp
```

Without `--foreground` the server detaches; check it with `wet server status` and stop it with `wet server stop`. With no config file the server binds `127.0.0.1:8000` with `auth = "no-auth"`. `no-auth` refuses any non-loopback bind, so this instance is localhost-only by construction. Override the bind with `--host` / `--port` or `WET_HOST` / `WET_PORT`. Several instances can run side by side on different ports.

To write a real config to edit:

```bash
uvx --python 3.13 --from n24q02m-wet wet config init   # writes ~/.wet/config.toml; --force overwrites
```

> **Search under `uvx`.** A server running from a `uvx` tool environment cannot start a local SearXNG. `search`, `research`, `docs`, and `similar` return an error there only when no backend in `SEARCH_BACKENDS` can run under `uvx`. The default chain `tavily,duckduckgo` always can, because DuckDuckGo is credential-free (see "Search backends").

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
printf '%s' '<token>' | uvx --python 3.13 --from n24q02m-wet wet token hash   # 2. print the scrypt$ hash (omit the pipe to be prompted)
```

3. Paste the printed `scrypt$...` value into `token_hash` and restart the server.
4. Give clients the **plaintext** token; they send it as `Authorization: Bearer <token>`. Do not write the plaintext token into any file you commit.

### `[models.*]` -- provider cells

Each task has its own independent cell with `base_url`, `api_key`, and `model`, spoken over OpenAI-compatible HTTP:

| Cell | Used for |
|---|---|
| `[models.embed]` | Embedding vectors for the docs index |
| `[models.rerank]` | Cross-encoder reranking of docs results |
| `[models.chat]` | LLM features: `expand`, `extract_structured`, `extract(action="agent")`, and keyword extraction for `similar` (which falls back to the page title without it) |
| `[models.jev_score]` | LLM-based scoring |

- OpenRouter is pre-wired as the default `base_url`. Any OpenAI-compatible endpoint works, cloud or local, and the cells can be mixed. Choose the models yourself.
- `api_key` may be left empty in the file and supplied by env instead: `HULL_EMBED_API_KEY`, `HULL_RERANK_API_KEY`, `HULL_CHAT_API_KEY`, `HULL_JEV_SCORE_API_KEY`. These are host-only and win over the file. `OPENROUTER_API_KEY` serves every cell that keeps the default OpenRouter `base_url`, and also the `openrouter` search backend.
- With no `embed`/`rerank` key, wet falls back to local ONNX models (downloaded on first use). With no `[models.chat]` key, the LLM-backed features are off.

### Changing the embedding model

Vectors from one embedding model cannot be searched with another, and the server refuses to boot after the model changes. Start it once with `REINDEX_ON_MODEL_CHANGE=true` to rebuild, then run `wet docs reembed` for any entry still missing a vector.

## Search backends

`SEARCH_BACKENDS` is an ordered, comma-separated fallback chain read by the server. Unset, the chain is `tavily,duckduckgo` (Tavily only when `TAVILY_API_KEY` is set). Keyed providers accept comma-separated keys for rotation.

| Backend | Needs |
|---|---|
| `searxng` | Opt-in only: a third-party instance at `SEARXNG_URL`, or a local SearXNG that wet installs and starts when `WET_AUTO_SEARXNG=true` (not under `uvx`, not with `DISABLE_LOCAL_SEARCH`) |
| `tavily` | `TAVILY_API_KEY` |
| `brave` | `BRAVE_API_KEY` |
| `exa` | `EXA_API_KEY` |
| `kagi` | `KAGI_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` (no default; the backend refuses to run without it), optionally `OPENROUTER_BASE_URL`, `OPENROUTER_SEARCH_ENGINE` |
| `firecrawl` | `FIRECRAWL_API_KEY` optional; keyless attempts are made when absent |
| `keenable` | `KEENABLE_API_KEY` optional; the keyless public endpoint is used when absent |
| `duckduckgo`, `startpage` | Nothing; credential-free. Datacenter IPs may hit bot challenges, and the chain then advances to the next backend. |

Every search response includes a `search_backend` trace: requested, attempted, selected, and a `fallback` state (`none`, `used`, `exhausted`, `unavailable`, or `parallel_fanout`).

## Browser backends

`BROWSER_BACKENDS` is an ordered list that selects how pages are rendered when extraction escalates: `native` (default when empty), `browserless` (a third-party managed instance via `BROWSERLESS_URL`, `BROWSERLESS_TOKEN`), and `invisible` (a stealth-Firefox tier from the `n24q02m-wet[invisible]` extra; `STEALTHFOX_BINARY` points at a patched Firefox build to skip the engine download). Setting `CAPSOLVER_API_KEY` appends a separate, key-gated CAPTCHA tier as the last escalation step. `BROWSER_BACKENDS` does not route `extract(action="interact")`, which always uses native Patchright sessions.

## Method 1: Claude Code plugin

The plugin installs six skills (`compare`, `fact-check`, `lock-project-stack`, `research-topic`, `scrape-batch`, `wet`), a SessionStart hook that warns when indexed docs are stale, and an HTTP MCP entry. wet is HTTP-only: the `wet` command from `n24q02m-wet` is the control-plane CLI, so the plugin does not launch a server. It connects to an instance you started yourself. Two plugin settings:

| Setting | Default | Meaning |
|---|---|---|
| `WET_URL` | `http://127.0.0.1:8000/mcp` | Streamable HTTP endpoint of your instance. Change it if the instance uses another port or host. |
| `WET_TOKEN` | empty | Bearer token for `auth = "token"` / `"multi"`; leave empty for a loopback `no-auth` instance. |

1. Start an instance first (see above): `wet server start`. Without a running instance `/mcp` shows `plugin:wet:wet` as failed (connection refused).
2. Install the plugin:
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install wet@n24q02m-plugins
   ```
3. Set `WET_URL` (and `WET_TOKEN` if needed) when Claude Code prompts for the plugin settings, then restart Claude Code and check `/mcp`.

## Method 2: local server + `claude mcp add`

```bash
uvx --python 3.13 --from n24q02m-wet wet server start
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

Start the compose stack (see "Always-on" above), then register `http://127.0.0.1:8000/mcp` with the Bearer header -- with `claude mcp add` as in Method 2.

## Method 4: remote host

Run the instance on a reachable host with `auth = "token"` or `"multi"`, and front it with a TLS proxy of your choice (the server itself serves plain HTTP). Clients use `https://<your-host>/mcp`:

```bash
claude mcp add --transport http wet https://<your-host>/mcp --header "Authorization: Bearer <token>"
```

Other remote clients connect the same way. claude.ai web adds the instance as a custom connector by its HTTPS URL. A connector added by URL is meant for a server hosted on the internet; for a server inside a private network, claude.ai needs an MCP tunnel, a research preview available to Claude Enterprise organizations by request (see [MCP tunnels](https://claude.com/docs/connectors/mcp-tunnels/overview)). To send the bearer token, choose **No sign-in** and add a request header `Authorization` with the value `Bearer <your-token>`. Request-header authentication is in beta and available to a limited set of organizations: if the connector dialog has no **Request headers** section, claude.ai cannot send the token, so it cannot use this server. See [Add a connector that isn't in the directory](https://claude.com/docs/connectors/custom/add-unlisted).

## Backup and migration

Server state lives under `~/.wet/` (in the `wet-home` and `wet-data` volumes for compose): `config.toml`, the SQLite (WAL) docs index `docs.db`, the web cache, and downloads. The server has no embedded sync; back up or move the directory with `rclone` or any file tool while the server is stopped. `wet docs import` loads a Cloudflare D1 SQL export into `docs.db`.

## Environment variables

Most settings live in `config.toml`. The server host also reads:

| Variable | Default | Description |
|---|---|---|
| `WET_HOST` / `WET_PORT` | from `[server]` | Override the bind address |
| `HULL_EMBED_API_KEY` / `HULL_RERANK_API_KEY` / `HULL_CHAT_API_KEY` / `HULL_JEV_SCORE_API_KEY` | -- | `api_key` for the matching `[models.*]` cell |
| `WET_HULL_DB` | `~/.hull/hull.db` | hull's shared provider key-pool store, used for the `[models.*]` cell keys and the search backend keys |
| `OPENROUTER_API_KEY` | -- | Default credential for OpenRouter cells and the `openrouter` search backend |
| `SEARCH_BACKENDS` | `tavily,duckduckgo` | Ordered search fallback chain |
| `TAVILY_API_KEY`, `BRAVE_API_KEY`, `EXA_API_KEY`, `KAGI_API_KEY`, `FIRECRAWL_API_KEY`, `KEENABLE_API_KEY` | -- | Keys for the matching search backends |
| `OPENROUTER_MODEL` | -- (required) | Model for the `openrouter` search backend; there is no default |
| `SEARXNG_URL` | `http://localhost:41592` | SearXNG instance for the opt-in `searxng` backend |
| `SEARXNG_AUTH_USER` / `SEARXNG_AUTH_PASS` | -- | Basic auth for an external SearXNG |
| `WET_AUTO_SEARXNG` | `false` | Auto-start a local SearXNG (never under `uvx` or with `DISABLE_LOCAL_SEARCH`) |
| `WET_SEARXNG_PORT` | `41592` | Port of that local SearXNG |
| `DISABLE_LOCAL_SEARCH` / `DISABLE_LOCAL_BROWSER` / `DISABLE_LOCAL_EMBED` / `DISABLE_LOCAL_RERANK` | `false` | Turn off the matching local resource |
| `WET_SEARCH_BUDGET` | `0` | Per-provider attempt budget per process (`0` = unlimited) |
| `BROWSER_BACKENDS` | -- (native) | Page renderer chain: `native`, `browserless`, `invisible` |
| `BROWSERLESS_URL` / `BROWSERLESS_TOKEN` | -- | Browserless endpoint and token |
| `STEALTHFOX_BINARY` | -- | Patched Firefox build for the `invisible` backend |
| `CAPSOLVER_API_KEY` | -- | Enables the optional key-gated CAPTCHA tier |
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
