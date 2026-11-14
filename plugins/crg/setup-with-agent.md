# Better Code Review Graph -- Agent Setup Guide

> Give this file to your AI agent to automatically set up crg.

## Method overview

crg is local-first. The plugin **defaults to stdio via plugin install** (`uvx`); the CLI and bundled skills are the primary surface and the MCP server is a secondary adapter. HTTP transport is opt-in and self-host only: you run the instance and authenticate clients with a Bearer token. There is no hosted endpoint, no OAuth flow, and no credential form.

> **Mutually exclusive -- pick one endpoint**: Do not stack `/plugin install` with a user `mcpServers` override for a manual stdio or HTTP endpoint. Both would load simultaneously, and the override would not include this plugin's skills or hooks. Use the default plugin install for the complete local-first experience.

## Option 1: Claude Code Plugin (Recommended)

The plugin runs the server in **stdio mode**. Graph storage is local SQLite, and local embeddings are resolved through Fastretrieval's ONNX model registry -- no external graph database and no API key required.

### Install prompts

When you run `/plugin install`, Claude Code prompts for the following optional fields (declared in `userConfig`). Sensitive values are stored in your system keychain and persist across `/plugin update`. Skipping all of them keeps the local default.

| Field | Required | Meaning |
|---|---|---|
| `EMBEDDING_MODELS` | Optional | CSV `provider/model,...`; the first entry is active, no runtime fallback. Empty = local embeddings |
| `LOCAL_EMBEDDING_MODEL` | Optional | Built-in Fastretrieval ID, or a manifest-backed artifact directory |
| `LOCAL_EMBEDDING_DIM` | Optional | Dimension for an external model ID without a manifest |
| `LOCAL_EMBEDDING_MODEL_FILE` | Optional | ONNX file inside a manifest-backed artifact (default `onnx/model.onnx`) |
| `LOCAL_EMBEDDING_POOLING` | Optional | `CLS`, `MEAN`, `LAST_TOKEN`, or `DISABLED` for an external ID without a manifest |
| `LOCAL_EMBEDDING_NORMALIZE` | Optional | L2 normalization for an external ID without a manifest |
| `LOCAL_RERANK_MODEL` | Optional | Fastretrieval `TextCrossEncoder` model ID; empty disables reranking |
| `HULL_EMBED_API_KEY` | Optional (sensitive) | Key for the `[models.embed]` cell, only for a cloud `EMBEDDING_MODELS` entry |
| `HULL_CHAT_API_KEY` | Optional (sensitive) | Key for the `[models.chat]` cell, only for LLM node summaries |

### Steps

```bash
# Install from marketplace (includes skills: impact-audit, onboard-repo, refactor-check, review-delta, review-pr, security-sweep + hooks)
/plugin marketplace add n24q02m/claude-plugins
/plugin install crg@n24q02m-plugins
```

The plugin includes SessionStart, UserPromptSubmit, and PostToolUse hooks. SessionStart reports whether a graph exists for the project, UserPromptSubmit warns when the graph is stale, and PostToolUse updates the graph incrementally after edits. Build the first graph with `graph(action="build")`.

## Environment Variables

All environment variables are **optional**. The server works with Fastretrieval's local ONNX embedding registry with zero configuration. crg does not read vendor-specific key variables (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `JINA_AI_API_KEY`, `COHERE_API_KEY`, and similar); keys go in the `[models.<task>]` cells of the instance config (`~/.crg/config.toml`, or `$CRG_CONFIG_DIR/config.toml`) or in the `HULL_*_API_KEY` variables below.

### Model Keys

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `HULL_EMBED_API_KEY` | No | -- | Host-injected key for the `[models.embed]` cell (OpenRouter pre-wired default); overrides the cell `api_key`. The model name still comes from `EMBEDDING_MODELS` |
| `HULL_CHAT_API_KEY` | No | -- | Host-injected key for the `[models.chat]` cell; enables LLM node summaries when the cell model is set |

### Embedding Configuration

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `EMBEDDING_MODELS` | No | empty | CSV embedding model selection (`provider/model,...`); the first entry is active, later entries are not runtime fallbacks |
| `DISABLE_LOCAL_EMBED` | No | unset | Skip the local ONNX download; embedding reports `unavailable` unless a cloud entry is configured |
| `LOCAL_EMBEDDING_MODEL` | No | -- | Optional BYO local embedding model ID; empty uses Fastretrieval's bundled model manifest |
| `LOCAL_EMBEDDING_MODEL_FILE` | No | `onnx/model.onnx` | ONNX file path for a BYO local embedding |
| `LOCAL_EMBEDDING_DIM` | No | `0` | Required for a BYO local embedding when no manifest provides dimensions |
| `LOCAL_EMBEDDING_POOLING` | No | `MEAN` | Pooling for a BYO local embedding (`MEAN`, `CLS`, `LAST_TOKEN`, or `DISABLED`) |
| `LOCAL_EMBEDDING_NORMALIZE` | No | `true` | Normalize BYO local embedding outputs |
| `LOCAL_RERANK_MODEL` | No | empty | Fastretrieval `TextCrossEncoder` model ID for query reranking; empty disables reranking |

Legacy: `EMBEDDING_MODEL` is deprecated and honored for one release with a warning; `EMBEDDING_BACKEND` is ignored with a warning. Use `EMBEDDING_MODELS`. The old summary-model and base-URL variables are no longer read; the summary model comes from the `[models.chat]` cell, and an unconfigured cell makes `graph(action="summarize")` return `status: skipped`.

crg has no cloud rerank consumer: do not configure `RERANK_MODELS` or `RERANK_API_BASE` for this server.

Cohere `embed-v4.0` uses exactly 1024-dimensional stored vectors; other backends keep 768. Do not compensate for a mismatch by slicing or padding. Run `graph(action="embed")` to replace stale vectors after a model change.

Graph state lives in the repository's `.crg/` directory. Older `.better-code-review-graph/`, `.code-review-graph/`, and `.code-review-graph.db` state is not migrated or adopted and is left untouched. After upgrading from such a version, first run `graph(action="build", full_rebuild=true)`, then embed if semantic search is needed, and re-apply desired suppression rules explicitly. See the [graph state reference](/servers/crg/setup/#graph-state).

### HTTP Mode (Self-Host)

Start an instance with `crg server start` (loopback, no-auth) or a container built from source (`docker compose up --build -d` in a clone of `n24q02m/crg`, token auth, `http://127.0.0.1:8772/mcp`). Auth and bind settings live in the instance `config.toml`, not in env vars. See [setup](/servers/crg/setup/#method-3-http-self-host).

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `MCP_TRANSPORT` | No | `stdio` | Set to `http` to run the HTTP transport (`TRANSPORT_MODE=http` also works, as does `--http`) |
| `MCP_HOST` | No | from config | Bind host; overrides `[server] host` |
| `MCP_PORT` | No | from config | Bind port; overrides `[server] port` |
| `CRG_CONFIG_DIR` | No | `~/.crg` | Directory holding the instance `config.toml` |
| `CRG_DATA_DIR` | No | `~/.crg` | Per-user data directory for multi-user graphs |

## Authentication

### Stdio Mode

No authentication. The server runs as your OS user against local checkouts. Optional model keys come from `HULL_*_API_KEY` env vars or the `[models.<task>]` cells in `config.toml`.

### HTTP Mode

Set `[server] auth` in `config.toml`: `no-auth` (loopback only), `token` (one shared Bearer token), or `multi` (per-user tokens via `users.toml`). For `token`, mint a token, run `crg token hash <token>`, paste the `scrypt$...` output into `token_hash`, and give clients the plaintext token as `Authorization: Bearer <token>`.

## Verification

After setup, verify the server is working by building the graph:

```
graph(action="build", repo_root="/path/to/your/repo")
```

Expected: returns a JSON summary with node counts, edge counts, and supported languages found.

Then try a search:

```
query(action="search", search_query="main function", repo_root="/path/to/your/repo")
```
