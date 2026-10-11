# Mnemo MCP -- Overview

Persistent, searchable long-term memory for AI agents. Store facts, preferences, and decisions once and recall them across sessions with hybrid natural-language and entity-graph search.

## What it does

- **Store and recall**: add memories with categories and tags; search by natural-language query, browse, update, and delete.
- **Entity knowledge graph**: relate memories to entities, walk a neighbourhood subgraph, view an entity timeline, and take a point-in-time (`as_of`) view of what was known at a given moment.
- **Lifecycle**: archive and restore, LLM-based consolidation and compression, and JSONL export/import for portability.

## Tools

Eleven single-purpose memory tools (the primary interface), the deprecated `memory` dispatcher that mirrors them and adds the entity graph, timeline, and point-in-time actions, and `config` for status, runtime settings, model warmup, and embedding backfill. Every action and parameter is listed in the [tools reference](/servers/mnemo-mcp/tools/).

## Deployment

mnemo is self-hosted and speaks Streamable HTTP only, on a single `/mcp` endpoint. Run an instance locally with `uvx --from mnemo-mcp mnemo-mcp` (loopback, no auth), as an always-on docker compose stack, or on a host of your own behind TLS with token or per-user (`multi`) auth. Any MCP client that supports HTTP servers connects to it -- Claude Code (with or without the plugin), Codex, Gemini CLI, Cursor, Windsurf, and claude.ai web for a remote instance.

All state is one SQLite database under `~/.mnemo/`; back it up or move it with any file tool, or use `export_memories` / `import_memories`.

## Configuration

Auth and providers live in the host-owned `~/.mnemo/config.toml`. Each task -- embedding, reranking, chat (compression, consolidation, importance scoring), and scoring -- has its own `[models.*]` cell with an OpenAI-compatible `base_url`, `api_key`, and `model`, so cloud and local providers can be mixed. With no embedding or rerank cell, mnemo uses local Fastretrieval ONNX models and needs no API key; an unconfigured cell never selects a paid provider. Full walkthrough in [setup](/servers/mnemo-mcp/setup/).

## Next steps

- [Setup](/servers/mnemo-mcp/setup/) -- start an instance and connect a client
- [Tools reference](/servers/mnemo-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/mnemo-mcp/troubleshooting/)
