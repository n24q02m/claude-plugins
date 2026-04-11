# Phase G6 — better-notion-mcp Streamable HTTP version + plugin.json inventory

Date: 2026-04-11
Executed by: Claude Code session (Phase G6 subagent)
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md`
Plan: `plans/2026-04-11-phase-g-unblock.md`

## better-notion-mcp Streamable HTTP evidence

### SDK version

- package.json pin: `^1.29.0`
- installed version: `1.29.0`

### Protocol version(s) declared by SDK

- `LATEST_PROTOCOL_VERSION = '2025-11-25'` (cjs/types.js:33, esm/types.js:2, cjs/types.d.ts:3, esm/types.d.ts:3)
- `SUPPORTED_PROTOCOL_VERSIONS = [LATEST_PROTOCOL_VERSION, '2025-06-18', '2025-03-26', '2024-11-05', '2024-10-07']` (cjs/types.js:35, esm/types.js:4)
- Draft constant present in `spec.types.{js,d.ts}`: `LATEST_PROTOCOL_VERSION = "DRAFT-2026-v1"` — declared but not the active runtime constant.

### Implementation file

- `src/transports/http.ts` imports `StreamableHTTPServerTransport` from `@modelcontextprotocol/sdk/server/streamableHttp.js` (line 9)
- Instantiated with `sessionIdGenerator: () => randomUUID()` (line 230) — Mcp-Session-Id management active
- Uses `requireBearerAuth`, `mcpAuthRouter` for OAuth 2.1 middleware (lines 7-8)

### Legacy SSE presence

- `SSEServerTransport` in `src/transports/`: **none** (grep returned no files)

## Verdict

**compliant**

- SDK 1.29.0 implements `2025-11-25`, the spec target.
- No legacy `SSEServerTransport` wired up.
- `StreamableHTTPServerTransport` is the sole HTTP transport.
- Phase J notion migration: no transport rewrite needed; only auth middleware swap to mcp-core.

Verdict mapping reference:

- **compliant**: SDK implements 2025-11-25, no legacy SSE. No transport rewrite in Phase J for notion; only auth middleware swap.
- **partial-newer-sdk-needed**: Uses `StreamableHTTPServerTransport` but SDK implements an older spec. Phase J needs SDK upgrade + re-test first.
- **non-compliant-legacy-sse-present**: Legacy `SSEServerTransport` still wired up. Phase J needs to remove SSE endpoint.
- **non-compliant-old-sdk**: SDK too old to support any 2025-xx spec. Phase J needs full SDK upgrade + rewrite.

## plugin.json format inventory (all 6 credential repos)

| Repo | Transport type | URL or command | Phase J action |
|------|---------------|----------------|----------------|
| better-notion-mcp | **http** (production) | https://better-notion-mcp.n24q02m.com/mcp | Reference template |
| wet-mcp | stdio | uvx --python 3.13 wet-mcp | Flip to type: http, local port 41601 |
| mnemo-mcp | stdio | uvx --python 3.13 mnemo-mcp | Flip to type: http, local port 41602 |
| better-code-review-graph | stdio | uvx --python 3.13 better-code-review-graph | Flip to type: http, local port 41603 |
| better-telegram-mcp | stdio | uvx --python 3.13 better-telegram-mcp | Flip to type: http, remote URL (Tier B) |
| better-email-mcp | stdio | npx -y @n24q02m/better-email-mcp | Flip to type: http, remote URL (Tier B) |

### Raw plugin.json mcpServers blocks

#### better-notion-mcp (template, type: http)

```json
"better-notion-mcp": {
  "type": "http",
  "url": "https://better-notion-mcp.n24q02m.com/mcp"
}
```

#### wet-mcp (stdio)

```json
"wet": {
  "command": "uvx",
  "args": ["--python", "3.13", "wet-mcp"]
}
```

#### mnemo-mcp (stdio)

```json
"mnemo": {
  "command": "uvx",
  "args": ["--python", "3.13", "mnemo-mcp"]
}
```

#### better-code-review-graph (stdio)

```json
"better-code-review-graph": {
  "command": "uvx",
  "args": ["--python", "3.13", "better-code-review-graph"]
}
```

#### better-telegram-mcp (stdio)

```json
"better-telegram-mcp": {
  "command": "uvx",
  "args": ["--python", "3.13", "better-telegram-mcp"]
}
```

#### better-email-mcp (stdio, npx)

```json
"better-email-mcp": {
  "command": "npx",
  "args": ["-y", "@n24q02m/better-email-mcp"]
}
```

notion is the template. Phase J per-repo migration duplicates this format with the appropriate URL/port.
