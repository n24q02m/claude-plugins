---
title: Tool layout standard (N+2)
description: Every server exposes N domain tools plus help and config.
---

Each MCP server in this stack exposes a uniform tool surface — **N domain tools + 2 universal tools**. The two universals are `help` and `config`. The N domain tools are server-specific.

## Why uniform

AI agents that switch between servers don't have to relearn navigation. Asking `wet-mcp.help()` and `mnemo-mcp.help()` returns the same shape — server description, tool list, mode, version, links. Same for `config()` — identical schema for credential introspection.

## The two universals

### `help`

Returns a structured description of the server: tagline, mode, tool count, tool names + brief descriptions, links to docs + repo. AI agents call this when uncertain which tool to use; humans call it for orientation.

Example response shape:

```json
{
  "name": "wet-mcp",
  "tagline": "Web search + content extraction + docs indexing.",
  "version": "2.1.0",
  "mode": "local-relay",
  "docs_url": "https://mcp.n24q02m.com/servers/wet-mcp/",
  "tools": [
    { "name": "search", "description": "Find URLs by keyword." },
    { "name": "extract", "description": "Read full text from a URL." },
    "..."
  ]
}
```

### `config`

Read-only access to server's current configuration: mode, public URL (remote modes), enabled features, credential presence (boolean only — never values). Used by AI agents to verify they're talking to the right deploy.

Example:

```json
{
  "mode": "remote-relay",
  "public_url": "https://wet-mcp.team.example",
  "features": ["search", "extract", "indexing"],
  "credentials_present": true
}
```

## Domain tools

Per-server. Designed for AI ergonomics — each tool is composite (one call replaces 3-5 raw API calls), returns schema-valid JSON, and includes structured error metadata when failures occur.

See each server's `/tools/` page for the per-server list.

## Why composite, not API mirror

Raw API mirrors leak too much surface to the agent. Example: Notion's REST API has 30+ endpoints — most agents don't need pagination, retries, schema lookups exposed. A composite `notion.create_page(title, content_md)` does pagination + parent lookup + markdown→blocks conversion in one call.

Memory `feedback_mcp_tool_layout.md` (mcp-dev skill) tracks the rule.

## Adding a new tool

When a new tool is added to a server, the `help` response auto-updates (tools list is generated from registered handlers). No separate doc to maintain.

## Anti-patterns

- N + 1 (only `help`, no `config`) → AI agents can't verify they're on the right deploy.
- Domain tool that requires multiple round-trips for common workflow → fold the round-trips into one composite tool.
- `help` that returns prose only, not structured JSON → AI agents can't parse reliably.
- Per-server `help` schemas that diverge → breaks "switch servers without relearning" property.
