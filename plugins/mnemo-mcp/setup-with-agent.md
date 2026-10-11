# Mnemo MCP -- Agent Setup Guide

> Give this file to your AI agent to set up mnemo-mcp.

mnemo is a self-hosted memory server that speaks **Streamable HTTP only** on a single `/mcp` endpoint. There is no stdio transport and no hosted public instance: the agent starts (or finds) an instance, then registers its endpoint with the client. Full reference: the [manual setup guide](/servers/mnemo-mcp/setup/).

## Step 1: Check for a running instance

Ask the user whether a mnemo instance already runs (a compose stack, a remote host, or a local `mnemo-mcp` process) and for its endpoint and token. If one exists, skip to Step 3.

## Step 2: Start an instance

Requires Python 3.13 and `uv`.

**Local, single user (no-auth, loopback only):**

```bash
uvx --from mnemo-mcp mnemo-mcp
# endpoint: http://127.0.0.1:8000/mcp
```

`no-auth` is the default and refuses any non-loopback bind, so no token is needed. Keep the process running (a terminal, a service manager, or the compose route below).

**Always-on or shared (token auth):** in a clone of `n24q02m/mnemo`:

```bash
cp mnemo-config/config.example.toml mnemo-config/config.toml
python -c "import secrets; print(secrets.token_urlsafe(32))"            # mint a token
MNEMO_AUTH_TOKEN=<token> uv run mnemo-mcp token-hash                     # print its scrypt$ hash
# edit mnemo-config/config.toml: [server] auth = "token", token_hash = "<scrypt$ hash>"
docker compose -f docker-compose.http.yml up --build -d
# endpoint: http://127.0.0.1:8771/mcp
```

Give the user the plaintext token and do not write it into any file in the repo; only the hash goes into `config.toml`.

**Provider cells (optional):** without `[models.embed]` / `[models.rerank]` cells mnemo uses the local Fastretrieval ONNX models. To use a cloud or local OpenAI-compatible endpoint, set `base_url`, `api_key`, and `model` per cell in `config.toml` (see `mnemo-config/config.example.toml`), or supply keys via `HULL_EMBED_API_KEY` / `HULL_RERANK_API_KEY` / `HULL_CHAT_API_KEY` / `HULL_JEV_SCORE_API_KEY`. Let the user choose models and keys -- do not pick paid providers on their behalf.

## Step 3: Register the endpoint

Choose **one** of the following per client; Claude Code matches servers by URL, so registering the same instance twice shows duplicates in `/mcp`.

**Claude Code plugin (adds the skills and hooks):**

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install mnemo-mcp@n24q02m-plugins
```

The install prompts ask for:

| Field | Value |
|---|---|
| `MNEMO_URL` | The instance endpoint from Step 1 or 2 |
| `MNEMO_TOKEN` | The plaintext token for `auth = "token"` / `"multi"`; empty for `no-auth` |

**Claude Code without the plugin:**

```bash
claude mcp add --transport http mnemo http://127.0.0.1:8000/mcp
# token auth: append --header "Authorization: Bearer <token>"
```

**Other clients** (Codex, Gemini CLI, Cursor, Windsurf, any `mcp.json`):

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

Drop `headers` for a `no-auth` instance. For a remote instance, use `https://<your-host>/mcp` behind a TLS proxy, with `auth = "token"` or `"multi"`.

## Step 4: Verify

Restart the client, then call:

```
memory_stats()
```

Expected: database statistics including the total memory count. `config(action="status")` additionally shows the auth mode and which provider cells are configured.

## Optional settings

- `config(action="warmup")` pre-downloads the local embedding model (~570 MB) so the first search is not slow.
- The plugin's PostToolUse capture hint is opt-in: `CAPTURE_AUTO_ENABLED=true`.
- Server env vars (`MNEMO_HOST`, `MNEMO_PORT`, `DB_PATH`, archive/dedup/rerank tuning, `KG_AUTO_ENABLED`, `LOG_LEVEL`) are listed in the [manual setup guide](/servers/mnemo-mcp/setup/#environment-variables).
