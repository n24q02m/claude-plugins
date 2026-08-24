# Better Code Review Graph -- Manual Setup Guide

> **2026-05-02 Update**: Plugin install (Method 1) now uses pure stdio mode. API keys are optional env vars.
> The previous "Zero-Config Relay" auto-spawn pattern has been removed.
> If you relied on the relay form to enter API keys, please:
> 1. Set the env var directly in plugin config (Method 1), OR
> 2. Use HTTP self-host mode (advanced; out of scope of this guide).

## Method overview

This plugin **defaults to stdio via plugin install** (`uvx`) -- the simplest path
and the one this guide covers in full. The repository keeps `stdio` and `http`
Dockerfile targets for source-built self-hosting, but new public OCI images are
no longer published. Historical registry tags remain untouched. HTTP remains a
self-host-only transport; there is no hosted CRG relay/OAuth runtime.

> **⚠️ Mutually exclusive — pick ONE per plugin**: Do NOT stack `/plugin install` AND a user `mcpServers` override (source-built Docker stdio or HTTP) — both would load simultaneously and create duplicate entries (plugin's `uvx` stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name — and `uvx` ≠ `docker` ≠ HTTP URL, so all three are distinct endpoints. Choosing the Docker stdio or HTTP self-host path means losing the plugin's skills/agents/hooks/commands. For full plugin features, use the default plugin install (Method 1) documented below.

## Prerequisites

- **Python 3.13** (3.14+ is NOT supported)
- `uv` or `uvx` installed ([docs](https://docs.astral.sh/uv/getting-started/installation/))
- Docker (optional, for containerized setup)
- A code repository to analyze

## Method 1: Claude Code Plugin (Recommended)

Plugin marketplace install runs the server in **pure stdio mode** with optional API key env vars. No daemon-bridge, no auto-spawn, no relay form. The graph is stored locally in SQLite -- no external graph database required.

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `JINA_AI_API_KEY` | Optional | https://jina.ai/api-key |
| `GEMINI_API_KEY` | Optional | https://aistudio.google.com/apikey |
| `OPENAI_API_KEY` | Optional | https://platform.openai.com/api-keys |
| `COHERE_API_KEY` | Optional | https://dashboard.cohere.com/api-keys |

### Steps

1. Open Claude Code.
2. Install the plugin (Claude Code prompts for `JINA_AI_API_KEY` -- press Enter to skip):
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-code-review-graph@n24q02m-plugins
   ```
3. The server starts automatically when Claude Code launches.
4. The SessionStart hook auto-builds the graph for the current project; PostToolUse updates it after edits.

## Credential Setup

All API keys are **optional**. The server works with local ONNX embeddings out of the box.

### Stdio Mode (Env Vars)

Set API keys in your MCP client `env` block or shell profile:

```bash
export JINA_AI_API_KEY="jina_..."
export GEMINI_API_KEY="AIza..."
```

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `JINA_AI_API_KEY` | No | -- | Jina AI: embedding + reranking (highest priority) |
| `GEMINI_API_KEY` | No | -- | Gemini: embedding (free tier). Also accepts `GOOGLE_API_KEY` |
| `GOOGLE_VERTEX_EXPRESS_API_KEY` | No | -- | Vertex AI Express: Gemini via API key, no Service Account. Get it at https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview |
| `OPENAI_API_KEY` | No | -- | OpenAI: embedding |
| `COHERE_API_KEY` | No | -- | Cohere: embedding + reranking. Also accepts `CO_API_KEY` |
| `EMBEDDING_BACKEND` | No | auto-detect | `cloud` or `local` (ONNX) |
| `EMBEDDING_MODEL` | No | auto-detect | Cloud embedding model name |
| `TRANSPORT_MODE` | No | `stdio` | Set to `http` to enable HTTP transport (multi-user). |
| `PUBLIC_URL` | Yes (http) | -- | Server's public URL for relay form. |
| `MCP_DCR_SERVER_SECRET` | Yes (http) | -- | HMAC secret for stateless Dynamic Client Registration. |
| `MCP_PORT` | No | `8080` | Server port (http mode only). |
| `LOG_LEVEL` | No | `INFO` | Logging level |

### Embedding Provider Priority

Cloud auto-detection order: Jina AI > Gemini > OpenAI > Cohere > local ONNX model

All embeddings are stored at a fixed embedding dimension. Switching providers does NOT invalidate existing vectors.

### Supported Languages

Python, TypeScript, JavaScript, Go, Rust, Java, C#, Ruby, Kotlin, Swift, PHP, C/C++, Solidity

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

Ensure the `repo_path` parameter points to the root of a code repository. Check that the project contains files in a supported language.

### First embedding is slow

On first use, the local ONNX embedding model (~570MB) is downloaded. Subsequent runs are instant. Use cloud embedding (any API key) to avoid this download.

### "No graph found" error

Build the graph first:

```
graph(action="build", repo_path="/path/to/your/repo")
```

### Source-built Docker cannot access repo files

Build the stdio target from the repository checkout, then mount the analyzed
repository at `/repo`:

```bash
git clone https://github.com/n24q02m/better-code-review-graph
cd better-code-review-graph
docker build --target stdio -t better-code-review-graph:local .
docker run -i --rm -v "/absolute/path/to/repo:/repo:ro" better-code-review-graph:local
```
