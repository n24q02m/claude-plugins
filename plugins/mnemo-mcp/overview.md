# Mnemo MCP -- Overview

Persistent, searchable long-term memory for AI agents. Store facts, preferences, and decisions once and recall them across sessions with hybrid natural-language and entity-graph search.

## What it does

- **Store and recall**: add memories with categories and tags; search by natural-language query, browse, update, and delete.
- **Entity knowledge graph**: relate memories to entities, walk a neighbourhood subgraph, view an entity timeline, and take a point-in-time (`as_of`) view of what was known at a given moment.
- **Lifecycle**: archive and restore, LLM-based consolidation and compression, and JSONL export/import for portability.
- Optional encrypted sync keeps a memory store consistent across machines.

## Tools

Eleven single-purpose memory tools (the primary interface) plus a consolidated `memory` dispatcher that mirrors them and adds the entity graph, timeline, and point-in-time actions. Every server in this stack also ships the two universal tools -- `config` (status, sync, runtime settings, credential setup) and `help`; `config__open_relay` reopens the browser setup form in HTTP mode. Every action and parameter is listed in the [tools reference](/servers/mnemo-mcp/tools/).

## Clients

Runs over stdio with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. Self-host the HTTP build for claude.ai web compatibility and multi-user, per-user isolation. See the [modes overview](/get-started/modes-overview/).

## Configuration

Works out of the box with a bundled local embedding model -- no keys required. Supply your own provider keys (`JINA_AI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`) as environment variables to use cloud embeddings or LLM-based consolidation. Use placeholders in shared config. Full walkthrough in [setup](/servers/mnemo-mcp/setup/).

## Next steps

- [Setup](/servers/mnemo-mcp/setup/) -- install and configure
- [Tools reference](/servers/mnemo-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/mnemo-mcp/troubleshooting/)
