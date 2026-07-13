# Mnemo MCP -- Tools Reference

mnemo-mcp exposes persistent AI memory through two layers: 11 single-purpose memory tools (the primary interface) plus a consolidated `memory` dispatcher tool that mirrors them and adds a few advanced actions. `config` manages server/sync settings, `help` returns full docs, and `config__open_relay` reopens the HTTP setup form. No tool wraps results as external/untrusted content -- memory entries are user-authored, not fetched from the open web.

## Single-purpose memory tools

| Tool | Purpose | Key parameters |
|---|---|---|
| `add_memory` | Store a new memory | `content` (required), `category`, `tags` |
| `search_memory` | Find memories by natural-language query | `query` (required), `category`, `tags`, `limit` (default 5, max 100) |
| `list_memories` | Browse memories | `category`, `limit` (default 5) |
| `update_memory` | Modify an existing memory | `memory_id` (required), `content`, `category`, `tags`, `source`, `importance` |
| `delete_memory` | Remove a memory by ID | `memory_id` (required) |
| `export_memories` | Export all memories as JSONL | -- |
| `import_memories` | Import memories from JSONL/list | `data` (required), `mode` (default `merge`) |
| `memory_stats` | Show database statistics | -- |
| `restore_memory` | Un-archive a memory | `memory_id` (required) |
| `archived_memories` | List archived memories | `limit` (default 5) |
| `consolidate_memories` | LLM-summarize a category into a condensed memory (requires an LLM key) | `category` (required) |

## memory

Consolidated dispatcher tool covering the same operations as the 11 tools above via an `action` parameter, plus a few advanced actions built on the entity/knowledge-graph layer.

| Action | Purpose | Key parameters |
|---|---|---|
| `add` / `search` / `list` / `update` / `delete` / `export` / `import` / `stats` / `restore` / `archived` / `consolidate` | Same as the single-purpose tools of the same name | See table above |
| `capture` | Typed capture with dedup (e.g. auto-capture from a conversation) | `text` (required, or `content`), `context_type` (default `conversation`), `category`, `tags`, `source`, `importance`, `auto` |
| `archive_now` | Trigger the score-based archive sweep on demand | -- |
| `compress` | Re-run LLM compression on an uncompressed memory | `memory_id` (required) |
| `entity_search` | Find memories by entity name | `name` (required, or `query`), `entity_type`, `limit` |
| `entity_graph` | Knowledge-graph neighborhood subgraph around an entity | `entity_id` or `name` (one required), `depth` (default 2), `limit` |
| `history` | Timeline of memories linked to an entity | `entity_id` (required, or `memory_id`) |
| `as_of` | Point-in-time view of memories valid at a given timestamp | `as_of` (required, ISO timestamp), `limit` (default 5, max 100) |

`as_of` returns `{memories, count, as_of}`. The `as_of` parameter is only valid with `action='as_of'` -- passing it alongside any other action returns an error instead of silently ignoring it, since point-in-time filtering isn't implemented for `search`/`list`.

## config

Server configuration, sync, and credential setup.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show config and database stats | -- |
| `sync` | Trigger a manual full Google Drive sync | -- |
| `set` | Update a runtime setting (`sync_enabled`, `sync_interval`, `log_level`) | `key` (required), `value` (required) |
| `warmup` | Pre-download the embedding model | -- |
| `setup_sync` | Start the Google Drive Device Code OAuth flow | -- |
| `setup_status` | Show credential state and configured providers | -- |
| `setup_start` | Start credential relay setup | `key` (`force` bypasses an already-configured guard); returns `stdio_unsupported` under stdio |
| `setup_skip` | Set local mode, skip the relay permanently | -- |
| `setup_reset` | Clear credential state | -- |
| `setup_complete` | Re-resolve credential state and re-init the embedding backend | -- |
| `setup_relay` | Alias for `setup_start(key="force")` | -- |
| `sync_now` | Passport-based delta sync (requires `SYNC_PASSPHRASE`) | `key` = backend name (optional, default via active backend) |
| `export_passport` | Write an encrypted passport bundle to disk (requires `SYNC_PASSPHRASE`) | -- |
| `import_passport` | Pull and apply a passport bundle (requires `SYNC_PASSPHRASE`) | `key` = source/backend name (optional) |

## help

Full documentation for the memory and config tools.

| Parameter | Values |
|---|---|
| `topic` | `memory` (default) \| `config` (`setup` is a back-compat alias for `config`) |

## config__open_relay

Opens the HTTP relay/credential setup form in the user's browser (self-host HTTP mode only). No parameters.
