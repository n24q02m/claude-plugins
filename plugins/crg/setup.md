# Better Code Review Graph -- Manual Setup Guide

crg is a local-first code knowledge graph. The repo is `n24q02m/crg`. Its primary surface is the `crg` CLI plus the bundled skills; the MCP server is a secondary adapter over the same graph code. The plugin installs from the PyPI package `better-code-review-graph`, which ships both the `crg` command and the legacy `better-code-review-graph` command.

`crg --help` lists the subcommands `config`, `db`, `graph`, `query`, `review`, `security`, `server`, and `token`. Run bare `crg` (no subcommand) to start the MCP server over stdio.

## Method overview

| Method | What runs where | Best for |
|---|---|---|
| **1. Plugin install (default)** | Claude Code plugin runs the server over stdio via `uvx`, plus skills and hooks | Claude Code users |
| **2. Manual stdio** | `uvx --python 3.13 better-code-review-graph` registered in any MCP client | Any stdio MCP client, no plugin |
| **3. HTTP self-host** | One instance you run (`crg server start`, or a container built from source), Bearer-token auth | Always-on instance shared across sessions and clients |

There is no hosted endpoint. HTTP is self-host only, and the server must have filesystem access to the repositories it indexes.

> **Pick ONE registration per client.** Claude Code matches MCP servers by **endpoint** (command string or URL), not by name. Installing the plugin *and* adding a manual `mcpServers` entry (stdio or HTTP) loads both and creates duplicates. A manual entry also loses the plugin's skills and hooks. For the full feature set use Method 1.

## Prerequisites

- **Python 3.13** (3.14+ is NOT supported)
- `uv` or `uvx` installed ([docs](https://docs.astral.sh/uv/getting-started/installation/))
- Docker (optional, for the containerized HTTP setup)
- A code repository to analyze

## Method 1: Claude Code Plugin (Recommended)

The plugin runs the server in **stdio mode**. The graph is stored locally in SQLite, and local embeddings are resolved through Fastretrieval's ONNX model registry -- no external graph database and no API key required.

### Install prompts

When you run `/plugin install`, Claude Code prompts for the following optional fields (declared in `userConfig`). Sensitive values are stored in your system keychain and persist across `/plugin update`. Skip all of them to keep the local default.

| Field | Required | Meaning |
|---|---|---|
| `EMBEDDING_MODELS` | Optional | CSV `provider/model,...`; the first entry is active, with no runtime fallback. Empty = local Fastretrieval embeddings |
| `LOCAL_EMBEDDING_MODEL` | Optional | Built-in Fastretrieval model ID, or a local directory containing `fastretrieval-manifest.json` |
| `LOCAL_EMBEDDING_DIM` | Optional | Output dimension; required for an external model ID without a manifest |
| `LOCAL_EMBEDDING_MODEL_FILE` | Optional | ONNX file path inside a manifest-backed artifact (default `onnx/model.onnx`) |
| `LOCAL_EMBEDDING_POOLING` | Optional | `CLS`, `MEAN`, `LAST_TOKEN`, or `DISABLED`, for an external ID without a manifest |
| `LOCAL_EMBEDDING_NORMALIZE` | Optional | L2 normalization for an external ID without a manifest |
| `LOCAL_RERANK_MODEL` | Optional | Fastretrieval `TextCrossEncoder` model ID; empty disables reranking |
| `HULL_EMBED_API_KEY` | Optional (sensitive) | Key for the `[models.embed]` cell; needed only for a cloud `EMBEDDING_MODELS` entry |
| `HULL_CHAT_API_KEY` | Optional (sensitive) | Key for the `[models.chat]` cell; needed only for LLM node summaries |

### Steps

1. Open Claude Code.
2. Install the plugin (skip the optional prompts to keep local embeddings):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install crg@n24q02m-plugins
   ```
3. The server starts automatically when Claude Code launches.
4. The SessionStart hook reports whether a graph exists for the current project; build it with `graph(action="build")`. After that, the PostToolUse hook updates it incrementally after edits.

## Method 2: Manual stdio

```bash
claude mcp add crg -- uvx --python 3.13 better-code-review-graph
```

Pass optional settings (see the reference below) in the client's `env` block. For other clients, register the same command under the client's stdio MCP configuration.

## Method 3: HTTP self-host

Use this when you want one always-on instance. The server speaks Streamable HTTP on `/mcp` and authenticates with a Bearer token minted by you. It has no OAuth flow and no credential form.

### Dev: no-auth, loopback only

```bash
uvx --python 3.13 --from better-code-review-graph crg server start
# MCP endpoint: http://127.0.0.1:8000/mcp
```

`crg server start` accepts `--host` and `--port`. With `auth = "no-auth"` the server refuses any bind outside loopback. You can also start HTTP by setting `MCP_TRANSPORT=http` (or `TRANSPORT_MODE=http`), or by passing `--http` to bare `crg`.

### Always-on: docker compose (token auth)

Public container images are no longer published; build from source. In a clone of `n24q02m/crg`:

```bash
cp docker-config/config.example.toml docker-config/config.toml   # then edit, see "Instance config"
docker compose up --build -d
# MCP endpoint: http://127.0.0.1:8772/mcp   (change the host port with CRG_PORT=9000)
```

The compose file builds the Dockerfile's `http` target, publishes only on `127.0.0.1`, keeps graph state in the `crg-data` volume, and mounts `docker-config/config.toml` read-only. Inside the container the server binds `0.0.0.0`, so the config **must** use `auth = "token"` or `"multi"`. For `auth = "multi"`, also mount `users.toml` (the commented line in the compose file).

To build the image without Compose: `docker build --target http .` (the `stdio` target also exists). The repository path inside the container is `/repo`.

### Instance config (`config.toml`)

All auth and provider settings live in a host-owned file at `$CRG_CONFIG_DIR/config.toml`, default `~/.crg/config.toml`. MCP clients never see it. `crg config init` writes a starter file, `crg config path` prints its location, and `crg config show` prints it.

| `[server]` key | Meaning |
|---|---|
| `host`, `port` | Bind address |
| `auth` | `no-auth` (loopback only), `token` (one shared Bearer token), or `multi` (per-user tokens and namespaces via `users.toml`) |
| `token_hash` | `scrypt$...` hash of the shared token. There is no plaintext token field |
| `rpm` | Optional rate limit |

With `auth = "multi"`, each namespace gets its own graph at `<CRG_DATA_DIR>/subs/<namespace>/graph.db`.

### Token setup (`auth = "token"`)

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"   # 1. mint a token
crg token hash <token>                                          # 2. print the scrypt$ hash
```

3. Paste the printed `scrypt$...` value into `token_hash` and restart the server.
4. Give clients the **plaintext** token; they send it as `Authorization: Bearer <token>`.

### Provider cells (`[models.<task>]`)

Each task has an independent cell with `base_url`, `api_key`, and `model`, spoken over OpenAI-compatible HTTP. OpenRouter is the pre-wired default `base_url`; any OpenAI-compatible endpoint works, cloud or local. `docker-config/config.example.toml` shows a complete set of example cells.

| Cell | Used by crg for |
|---|---|
| `[models.embed]` | Cloud embeddings (the model name still comes from `EMBEDDING_MODELS`) |
| `[models.chat]` | LLM node summaries (`graph(action="summarize")`); the cell's `model` is the summary model |

`api_key` may be left empty in the file and supplied by env instead: `HULL_EMBED_API_KEY`, `HULL_CHAT_API_KEY` (and `HULL_RERANK_API_KEY`, `HULL_JEV_SCORE_API_KEY` for the other two cells in the schema). These keys are host-only; end users never supply them. The same cells apply to stdio, where `~/.crg/config.toml` is read.

Client config for an HTTP instance:

```json
{
  "mcpServers": {
    "crg": {
      "url": "http://127.0.0.1:8772/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

## Environment Variable Reference

crg reads only the variables below. Vendor-specific key variables (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `JINA_AI_API_KEY`, `COHERE_API_KEY`, `OPENROUTER_API_KEY`, and similar) are **not read**; supply keys through the `[models.<task>]` cells or the `HULL_*_API_KEY` variables.

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `EMBEDDING_MODELS` | No | empty | CSV embedding model selection (`provider/model,...`); the first entry is active, later entries are not runtime fallbacks. Empty uses the local model. A cloud entry also needs a configured `[models.embed]` cell with a key |
| `DISABLE_LOCAL_EMBED` | No | unset | Skip the local ONNX download; embedding reports `unavailable` unless a cloud entry is configured |
| `LOCAL_EMBEDDING_MODEL` | No | -- | Optional BYO local embedding model ID or manifest directory; empty uses Fastretrieval's bundled model manifest |
| `LOCAL_EMBEDDING_MODEL_FILE` | No | `onnx/model.onnx` | ONNX file path for a BYO local embedding |
| `LOCAL_EMBEDDING_DIM` | No | `0` | Required for a BYO local embedding when no manifest provides dimensions |
| `LOCAL_EMBEDDING_POOLING` | No | `MEAN` | Pooling for a BYO local embedding (`MEAN`, `CLS`, `LAST_TOKEN`, or `DISABLED`) |
| `LOCAL_EMBEDDING_NORMALIZE` | No | `true` | Normalize BYO local embedding outputs |
| `LOCAL_RERANK_MODEL` | No | empty | Fastretrieval `TextCrossEncoder` model ID for query reranking; empty disables reranking |
| `HULL_EMBED_API_KEY` | No | -- | Host-injected key for the `[models.embed]` cell; overrides the cell `api_key` |
| `HULL_CHAT_API_KEY` | No | -- | Host-injected key for the `[models.chat]` cell; enables LLM summaries when the cell model is set |
| `CRG_CONFIG_DIR` | No | `~/.crg` | Directory holding the instance `config.toml` |
| `CRG_DATA_DIR` | No | `~/.crg` | Per-user data directory for HTTP multi-user graphs |
| `MCP_TRANSPORT` | No | `stdio` | Set to `http` to run the HTTP transport (`TRANSPORT_MODE=http` also works) |
| `MCP_HOST` | No | from config | Bind host for HTTP mode; overrides `[server] host` |
| `MCP_PORT` | No | from config | Bind port for HTTP mode; overrides `[server] port` |

Legacy aliases: `EMBEDDING_MODEL` is deprecated and honored for one release with a warning; migrate to `EMBEDDING_MODELS`. `EMBEDDING_BACKEND` is ignored with a warning. The old summary-model and base-URL variables are no longer read.

### Embedding provider selection

- **Cloud**: a non-empty `EMBEDDING_MODELS` value selects its first `provider/model`. The model prefix (`cohere/`, `jina_ai/`, ...) only picks wire details such as Cohere's `input_type`; it never selects a key or transport. The `[models.embed]` cell must carry a key, otherwise embedding reports an error.
- **Local**: an empty chain resolves Fastretrieval's local ONNX model registry (the first run downloads about 570 MB). Set `LOCAL_EMBEDDING_MODEL` only for a BYO local model.
- **Custom local metadata**: a BYO model can use `LOCAL_EMBEDDING_MODEL_FILE`, `LOCAL_EMBEDDING_DIM`, `LOCAL_EMBEDDING_POOLING`, and `LOCAL_EMBEDDING_NORMALIZE`; manifest-backed models supply their own metadata. A directory without a manifest, or an unknown ID without a dimension, is rejected rather than replaced by the default model.

Embeddings are tagged with the active provider/model identity. Cohere `embed-v4.0` stores exactly **1024 dimensions**; other backends keep 768-dimensional storage. crg does not slice or pad provider vectors. Run `graph(action="embed")` after changing models. Document embeddings use `search_document`; queries use `search_query`.

Query reranking is local and opt-in through `LOCAL_RERANK_MODEL`. crg has no cloud reranking provider and does not read `RERANK_MODELS` or `RERANK_API_BASE`. When enabled, semantic search reranks a bounded candidate pool and returns a `rerank_score`; a reranker failure is reported as an error instead of silently falling back.

Node summaries use the `model` of the `[models.chat]` cell. If the cell is not configured, `graph(action="summarize")` returns `status: skipped` with `reason: no_provider_configured`. There is no local-summary fallback, and a bare key does not enable summaries.

### Graph state

The graph database, security scan cache, and suppression list live in the repository's `.crg/` directory (graph at `.crg/graph.db`; the directory ignores itself). Older state under `.better-code-review-graph/`, `.code-review-graph/`, and `.code-review-graph.db` is not migrated or adopted and is left untouched. After upgrading from such a version, run `graph(action="build", full_rebuild=true)`, then `graph(action="embed")` if semantic search is needed, and re-apply any suppression rules explicitly.

### Supported Languages

Python, TypeScript, JavaScript, Go, Rust, Java, C#, Ruby, Kotlin, Swift, PHP, C/C++

### Ignore Files

Create `.code-review-graphignore` in your project root to exclude paths:

```
generated/**
*.generated.ts
vendor/**
node_modules/**
```

## Troubleshooting

### Graph build finds no files

Ensure the repository root points at a code repository (`repo_root` in tools, `--repo-root` on the CLI). Check that the project contains files in a supported language.

### First embedding is slow

On first use, Fastretrieval's local ONNX embedding model (about 570 MB) is downloaded. Subsequent runs are instant. Configure a cloud embedding entry to avoid the download.

### "No graph found" error

Build the graph first:

```
graph(action="build", repo_root="/path/to/your/repo")
```

### Docker cannot access repo files

Build from a reviewed release tag, then verify the volume mount. The repository path inside the container is `/repo`:

```bash
git clone --branch <release-tag> --depth 1 https://github.com/n24q02m/crg.git
cd crg
docker build --target stdio -t crg:stdio .
docker run -i --rm -v "/absolute/path/to/repo:/repo:ro" crg:stdio
```

More in the [troubleshooting guide](/servers/crg/troubleshooting/).
