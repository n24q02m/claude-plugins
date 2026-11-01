# WET (Web Extended Toolkit) -- Agent Setup Guide

Give this file to your AI agent so it can set up wet for you. wet is a self-hosted MCP server that speaks Streamable HTTP only (a single `/mcp` endpoint); there is no stdio transport and no hosted public instance. The agent starts an instance, then registers its URL with your client.

## Step 1: Check for a running instance

```bash
uvx --python 3.13 --from wet-mcp wet server status
```

It reports the pid, the lock, and whether HTTP is up on the configured port (default 8000). If HTTP is up, note the endpoint (`http://127.0.0.1:8000/mcp` for the default port) and skip to Step 3.

## Step 2: Start an instance

Python 3.13 is required (3.14+ is not supported).

**Local, no-auth (loopback only):**

```bash
uvx --python 3.13 --from wet-mcp wet server start
```

This detaches and binds `127.0.0.1:8000` with `auth = "no-auth"`, which refuses any non-loopback bind. Use `--foreground` to keep it attached. Because a `uvx` server cannot auto-start local SearXNG, set a search backend on the host before starting, for example `SEARCH_BACKENDS=duckduckgo,startpage` (credential-free), or a keyed provider such as `tavily` with `TAVILY_API_KEY`.

**Always-on, token auth (docker compose):**

1. In a clone of `n24q02m/wet`, run `cp docker-config/config.example.toml docker-config/config.toml`.
2. Mint a token and hash it: `openssl rand -hex 32`, then `uvx --python 3.13 --from wet-mcp wet token hash <token>`.
3. Put only the printed `scrypt$...` value in `token_hash` in `docker-config/config.toml`. Never write the plaintext token into a file that could be committed; hand it to the user or the client config only.
4. Run `docker compose up --build -d`. The endpoint is `http://127.0.0.1:8000/mcp` (change the host port with `WET_PORT`).

**Provider cells:** embedding, reranking, and LLM tasks use `[models.*]` cells in `~/.wet/config.toml`. Ask the user which models and keys to use; do not pick a paid provider on their behalf. With no embed/rerank key, wet uses local ONNX models; with no chat key, the LLM-backed features are off.

## Step 3: Register the instance with the client

**Claude Code plugin:**

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install wet@n24q02m-plugins
```

At the install prompts, set `WET_URL` to the endpoint and, for a token-auth instance, `WET_TOKEN` to the plaintext token. Leave `WET_TOKEN` empty for a loopback `no-auth` instance. Do not also run `claude mcp add` for the same URL; Claude Code matches servers by endpoint and would show duplicates.

**Claude Code without the plugin:**

```bash
claude mcp add --transport http wet http://127.0.0.1:8000/mcp
# token-auth instance: add --header "Authorization: Bearer <token>"
```

**Other clients (Codex, Gemini CLI, Cursor, Windsurf):** register the same URL in the client's MCP settings:

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

Drop `headers` for a `no-auth` instance. For a remote host behind TLS, use `https://<your-host>/mcp`.

## Step 4: Verify

Restart the client, confirm `wet` appears in `/mcp`, then call:

```
search(action="search", query="test query", max_results=3)
config(action="status")
```

`search` should return results with a `search_backend` trace; `config(action="status")` shows the auth mode, docs database, embed/rerank backend, cache, and SearXNG state.

## Optional settings

- `wet warmup` or `config(action="warmup")` pre-downloads enabled local resources so the first call is not slow.
- Search chain, browser backends, cache, and other server-host settings are environment variables on the host: see [Environment variables](/servers/wet/setup/#environment-variables).
