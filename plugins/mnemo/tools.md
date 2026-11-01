# Mnemo MCP -- Tools Reference

mnemo-mcp exposes persistent AI memory through 13 tools: 11 single-purpose memory tools (the recommended interface), the deprecated `memory` dispatcher that mirrors them and adds the entity-graph and point-in-time actions, and `config` for server status and runtime settings. No tool wraps results as external/untrusted content -- memory entries are user-authored, not fetched from the open web.

Every `limit` parameter is clamped to 1-100.

## Single-purpose memory tools

| Tool | Purpose | Key parameters |
|---|---|---|
| `add_memory` | Store a new memory | `content` (required), `category`, `tags` |
| `search_memory` | Find memories by natural-language query | `query` (required), `category`, `tags`, `limit` (default 5) |
| `list_memories` | Browse memories | `category`, `limit` (default 5) |
| `update_memory` | Modify an existing memory | `memory_id` (required), `content`, `category`, `tags`, `source`, `importance` |
| `delete_memory` | Remove a memory by ID | `memory_id` (required) |
| `export_memories` | Export all memories as JSONL | -- |
| `import_memories` | Import memories from a JSONL string or a list | `data` (required), `mode` (default `merge`) |
| `memory_stats` | Show database statistics | -- |
| `restore_memory` | Un-archive a memory | `memory_id` (required) |
| `archived_memories` | List archived memories | `limit` (default 5) |
| `consolidate_memories` | LLM-summarize a category into a condensed memory (needs the `[models.chat]` cell) | `category` (required) |

## memory

**Deprecated** legacy dispatcher -- prefer the single-purpose tools above; it will be removed in a future release. Every response carries a `_deprecation` notice. It covers the same operations via an `action` parameter, plus the actions built on the entity/knowledge-graph layer, which have no single-purpose equivalent yet.

| Action | Purpose | Key parameters |
|---|---|---|
| `add` / `list` / `update` / `delete` / `export` / `import` / `stats` / `restore` / `archived` / `consolidate` | Same as the single-purpose tool of the same name | See the table above |
| `search` | Hybrid search, with filters the single-purpose tool lacks | `query` (required), `category`, `tags`, `limit`, `context_type`, `since`, `until`, `min_importance` (default `0.0`), `include_archived` (default `false`) |
| `capture` | Typed capture with dedup (e.g. auto-capture from a conversation) | `text` (required, or `content`), `context_type` (default `conversation`), `category`, `tags`, `source`, `importance`, `auto` (default `false`) |
| `archive_now` | Run the score-based archive sweep on demand | -- |
| `compress` | Re-run LLM compression on an uncompressed memory | `memory_id` (required) |
| `entity_search` | Find memories by entity name | `name` (required, or `query`), `context_type` = entity type filter (`person`, `project`, `tool`, `concept`, `org`, `location`, `event`), `limit` |
| `entity_graph` | Knowledge-graph neighborhood subgraph around an entity | `entity_id` or `name`/`query` (one required), `depth` (default 2), `limit` |
| `history` | Timeline of memories linked to an entity | `entity_id` (required, or `memory_id`) |
| `as_of` | Point-in-time view of memories valid at a given timestamp | `as_of` (required, ISO timestamp), `limit` (default 5) |

`as_of` returns `{memories, count, as_of}`. The `as_of` parameter is only valid with `action='as_of'` -- passing it alongside any other action returns an error instead of silently ignoring it, since point-in-time filtering isn't implemented for `search`/`list`.

`entity_search` takes the entity type through `context_type`; there is no separate `entity_type` parameter.

## config

Server status and runtime settings. Auth, bind address, and provider cells live in the host-owned `~/.mnemo/config.toml` and are not editable through this tool.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show config, provider cells, auth mode, and database stats | -- |
| `set` | Update a runtime setting (only `log_level`) | `key` (required), `value` (required) |
| `warmup` | Pre-download the local embedding model, or probe the `[models.embed]` cell when one is configured | -- |
| `backfill_embeddings` | Embed memories that are missing a vector | `batch_size` (optional, max 100) |

## Resources and prompts

| URI / Prompt | Parameters | Description |
|---|---|---|
| `mnemo://stats` | -- | Database statistics and server status (resource) |
| `save_summary` | `summary` | Prompt to save a conversation summary as memory |
| `recall_context` | `topic` | Prompt to recall relevant memories about a topic |
