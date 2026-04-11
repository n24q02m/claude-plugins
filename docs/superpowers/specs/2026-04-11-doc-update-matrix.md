# Doc Update Matrix — Phase 3 MCP Core Migration

**Companion to**: `specs/2026-04-10-mcp-core-unified-transport-design.md`
**Date**: 2026-04-11
**Status**: Draft
**Purpose**: File-level inventory of every doc/config file that must be updated during Phase J (per-repo migration), grouped by repo. Each row shows current state vs target state. No placeholders — every line is concrete.

---

## 1. 6 × `.claude-plugin/plugin.json` (per credential repo)

Flip `"command": "uvx"` stdio entry → `"type": "http"` entry. Reference production format: `better-notion-mcp/.claude-plugin/plugin.json` already uses this format.

### wet-mcp (Tier A — local only)

**Before** (current):
```json
{
  "name": "wet-mcp",
  "description": "Web search, content extraction, and media download",
  "version": "2.24.0",
  "mcpServers": {
    "wet": {
      "command": "uvx",
      "args": ["--python", "3.13", "wet-mcp"]
    }
  }
}
```

**After** (Phase J):
```json
{
  "name": "wet-mcp",
  "description": "Web search, content extraction, and media download",
  "version": "3.0.0",
  "mcpServers": {
    "wet": {
      "type": "http",
      "url": "http://127.0.0.1:41601/mcp",
      "headers": { "Authorization": "Bearer ${WET_MCP_BEARER_TOKEN}" }
    }
  }
}
```

Port 41601 is arbitrary — pick from free range. Document in README. Bearer token resolved at agent startup via `mcp_core.install.agents` module during first install.

### mnemo-mcp (Tier A — local only)

Port 41602. Same pattern.

### better-code-review-graph (Tier A — local only)

Port 41603. Same pattern.

### better-telegram-mcp (Tier B — local + remote mandatory)

Ship with **remote production URL**, fall back local if user sets `MCP_USE_LOCAL=1`:

```json
{
  "name": "better-telegram-mcp",
  "version": "5.0.0",
  "mcpServers": {
    "better-telegram-mcp": {
      "type": "http",
      "url": "https://better-telegram-mcp.n24q02m.com/mcp"
    }
  }
}
```

Deploy target `oci-vm-prod`. Local alternative (port 41604) documented in setup-manual.md as "Option: self-run local".

### better-email-mcp (Tier B)

Same pattern as telegram. URL `https://better-email-mcp.n24q02m.com/mcp`. Local port 41605.

### better-notion-mcp (Tier B — already production)

**Current** already uses `"type": "http"` with `https://better-notion-mcp.n24q02m.com/mcp`. Only changes:
- Version bump to `3.0.0` (aligned with Phase 3 release)
- Add local fallback section in `setup-manual.md`

### better-godot-mcp (Tier C — unchanged)

Keep stdio. Only version bump.

---

## 2. 12 × `docs/setup-with-agent.md` + `docs/setup-manual.md` (per credential repo)

Every repo's 2 setup docs need 4 changes:

**Change A — Option 1 (Claude Code Plugin) unchanged** — marketplace install path still works because plugin.json updated.

**Change B — Option 2 (MCP Direct) stdio → HTTP**

Before (current, wet-mcp example):
```
### Claude Code (settings.json)
Add to `~/.claude/settings.local.json` under `"mcpServers"`:
{
  "mcpServers": {
    "wet": {
      "command": "uvx",
      "args": ["--python", "3.13", "wet-mcp"]
    }
  }
}
```

After:
```
### Claude Code (settings.json)
Add to `~/.claude/settings.local.json` under `"mcpServers"`:
{
  "mcpServers": {
    "wet": {
      "type": "http",
      "url": "http://127.0.0.1:41601/mcp"
    }
  }
}
```

Note: Bearer token is auto-injected on first OAuth dance. Users do not paste tokens manually.

Similar for Codex CLI config.toml and OpenCode opencode.json entries.

**Change C — Credential section: relay form → OAuth 2.1 authorization page**

Replace "Zero-Config Relay" subsection (lines ~131-144 in setup-manual.md) with:

```
### Zero-Config OAuth Authorization

On first tool call, the server returns HTTP 401 with a browser link.
Your agent (Claude Code, Codex, Copilot, etc.) automatically opens
the browser to an authorization page where you enter API keys.

Supported agents (auto-browser on 401):
- Claude Code, Claude Code Insiders
- Codex CLI
- GitHub Copilot (VSCode Insiders)
- Cursor, Windsurf, Antigravity, OpenCode

Manual agents: if your agent doesn't auto-open, copy the URL from
the server stderr and open it manually.

Credentials are encrypted with AES-256-GCM machine key and stored
at `~/.config/mcp/config.enc`. No environment variables needed.
```

**Change D — Add "HTTP daemon management" section**

New section in both docs explaining:
- Server runs as long-lived HTTP daemon on first agent connect
- Managed via MCP tool actions: `status`, `shutdown_daemon`, `reset_credentials`, `install_agent`
- Auto-ensure: stdio proxy launcher auto-starts daemon if not running (cross-platform file lock)
- Config location: `~/.config/mcp/` (config.enc, bearer.token, server.lock)

**Change E — Remove stdio mode references** (wet, mnemo, crg, telegram, email, notion)

Scan all mentions of:
- `"command": "uvx"`, `"command": "npx"`
- `StdioServerTransport`
- `stdio_client`, `StdioClientTransport`
- "Connect via stdio"
- `MCP_RELAY_URL` env (replaced with OAuth discovery)

Replace or delete per context.

Total: 6 repos × 2 files = **12 files** with changes A through E.

---

## 3. 6 × `README.md` (per credential repo)

Update Setup section (line ~33-40 depending on repo) to point users to `docs/setup-with-agent.md` as primary. Remove inline stdio examples. Add prominent "HTTP + OAuth 2.1" badge/note at top.

Pattern:

```markdown
## Setup

- **Quick (Claude Code)**: `/plugin marketplace add n24q02m/claude-plugins && /plugin install <name>@n24q02m-plugins`
- **Other agents**: see [docs/setup-with-agent.md](docs/setup-with-agent.md)
- **Manual**: see [docs/setup-manual.md](docs/setup-manual.md)

All servers use Streamable HTTP 2025-11-25 with OAuth 2.1 authorization.
Agents automatically open the authorization page on first tool call.
```

6 repos × 1 file = **6 files**.

---

## 4. Profile README — `C:/Users/n24q02m-wlap/projects/n24q02m/README.md`

Update 3 sections:

**Section "Servers" table (line 17-23)**: No structural change. Guide links still point to `setup-with-agent.md`. Optional: add `Transport` column showing HTTP/stdio.

**Section "Design Philosophy" principle #6 (line 36)**:

Before:
```
6. **Multi-User HTTP Mode** -- Stateless DCR (HMAC-SHA256), per-user session isolation, AES-256-GCM credential encryption at rest, OAuth 2.1 + PKCE S256.
```

After:
```
6. **Streamable HTTP 2025-11-25 Default** -- All MCP servers default to Streamable HTTP local transport. stdio exists only as thin proxy for agents lacking HTTP support. OAuth 2.1 + PKCE S256 with stateless DCR (HMAC-SHA256), per-user session isolation, AES-256-GCM credential encryption at rest. Light servers (telegram/email/notion) also support multi-user remote mode; heavy servers (wet/mnemo/crg) default local, remote opt-in self-host. Godot is stdio-only (no credentials).
```

**Section "Libraries" table (line 44)**:

Before:
```
| [mcp-relay-core](https://github.com/n24q02m/mcp-relay-core) | Cross-language relay infrastructure for MCP servers (ECDH crypto, config storage, relay client) | `npm i @n24q02m/mcp-relay-core` / `pip install mcp-relay-core` |
```

After:
```
| [mcp-core](https://github.com/n24q02m/mcp-core) | Unified MCP Streamable HTTP transport, OAuth 2.1 AS, lifecycle, install, and shared embedding daemon | `npm i @n24q02m/mcp-core` / `pip install mcp-core` |
```

1 file.

---

## 5. Skill reference — `C:/Users/n24q02m-wlap/projects/n24q02m/skills/fullstack-dev/references/mcp-server.md`

Update 5 locations (line numbers approximate, re-grep before editing):

**Line 123 + 132 — Transport example**:

Before:
```json
{
  "transport": { "type": "stdio" }
}
```

After:
```json
{
  "transport": { "type": "http", "port": 41601 }
}
```

Add secondary example showing stdio with comment "fallback only for agents without HTTP support".

**Line 315-324 — Agent compatibility matrix**:

Add column "Streamable HTTP 2025-11-25" with Yes/No per agent. Update existing "stdio/sse/http" column to be more specific.

**Line 588-640 — Code example `StdioServerTransport`**:

Reorder: Streamable HTTP example FIRST (primary), stdio example SECOND (labeled "legacy, for Godot or HTTP-incapable agents").

Streamable HTTP Python example:
```python
from fastmcp import FastMCP
from mcp_core.transport import StreamableHTTPServer

mcp = FastMCP("my-server")

@mcp.tool()
def my_tool(arg: str) -> str:
    return f"result for {arg}"

if __name__ == "__main__":
    StreamableHTTPServer(mcp).run(host="127.0.0.1", port=41601)
```

**Line 757-800 — E2E test pattern**:

Add HTTP client test pattern using `httpx.AsyncClient`:

```python
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://127.0.0.1:41601/mcp") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("my_tool", {"arg": "value"})
```

Keep existing stdio example below, labeled "legacy/godot only".

**Line 1117 — Principle #1 Zero-Knowledge Relay**:

Before (Vietnamese):
```
### 1. Zero-Knowledge Relay
Relay server KHONG BAO GIO thay plaintext credentials. E2E encryption: ECDH P-256 key exchange + AES-256-GCM. URL fragment (`#k=...&p=...`) chua secrets — theo RFC 3986, fragment KHONG gui toi server.
```

After:
```
### 1. OAuth 2.1 Authorization with Zero-Knowledge Storage
Server tự làm OAuth 2.1 Authorization Server (self-hosted AS). Authorization page hiển thị form nhận credentials user submit, server lưu encrypted (AES-256-GCM machine key) locally tại `~/.config/mcp/config.enc`. Tool code không bao giờ thấy plaintext credentials — chỉ access qua `Depends(get_session_creds)` injected từ transport middleware. Notion là ngoại lệ remote mode: delegate sang Notion OAuth thật cho multi-user.
```

1 file.

---

## 6. Global rules — `~/.claude/CLAUDE.md`

Section 3 "E2E TESTING (MCP SERVERS)" needs augmentation. Current content mentions only `stdio_client`. Add HTTP client path:

Before:
```
- **MCP protocol**: Test qua `mcp.ClientSession` + `stdio_client` (initialize → tools/list → tools/call). **KHÔNG BAO GIỜ** import Python functions trực tiếp.
```

After:
```
- **MCP protocol**: Test qua `mcp.ClientSession`. Transport chọn theo server:
  - **HTTP (default for credential servers)**: `streamablehttp_client("http://127.0.0.1:<port>/mcp")` — test OAuth dance empirically, verify Bearer token flow
  - **stdio (godot only)**: `stdio_client` với `StdioServerParameters`
  - **KHÔNG BAO GIỜ** import Python functions trực tiếp
```

1 file.

---

## 7. Claude-plugins marketplace — `.claude-plugin/marketplace.json`

Verify entry for each of 7 plugins reflects new version after Phase J release. No structural changes expected — marketplace.json aggregates plugin.json version fields.

1 file.

---

## 8. Summary table

| Category | Count | Files |
|----------|------:|-------|
| plugin.json (credential repos) | 6 | wet, mnemo, crg, telegram, email, notion |
| setup-with-agent.md | 6 | same |
| setup-manual.md | 6 | same |
| README.md (credential repos) | 6 | same |
| Profile README | 1 | n24q02m/README.md |
| Skill reference mcp-server.md | 1 | n24q02m/skills/fullstack-dev/references/mcp-server.md |
| Global CLAUDE.md | 1 | ~/.claude/CLAUDE.md |
| Marketplace manifest | 1 | claude-plugins/.claude-plugin/marketplace.json |
| **Total** | **28** | |

Plus **3 files deleted per credential repo** (`credential_state.py` + test + optional `setup_tool.py` bits) × 6 = ~18 file deletions.

Plus **6 servers' `server.py`** refactored to drop AWAITING_SETUP block.

---

## 9. Ordering note for Phase J

For each repo in Phase J, follow this exact order to avoid breaking intermediate states:

1. Add `mcp-core` dep (assumes Phase I done)
2. Update imports (`mcp_relay_core` → `mcp_core`)
3. Rewrite entry point (`server.py` or `src/server.ts`) to use `StreamableHTTPServer` from `mcp-core`
4. Delete `credential_state.py` + tests
5. Delete AWAITING_SETUP blocks in `server.py`
6. Add `Depends(get_session_creds)` injections in tool handlers
7. Update `sync.py` scope (wet + mnemo only) to `drive.appdata`
8. Update `hooks/hooks.json` (CRG only) to HTTP POST
9. Update `.claude-plugin/plugin.json` to `"type": "http"`
10. Update `docs/setup-with-agent.md`
11. Update `docs/setup-manual.md`
12. Update `README.md` Setup section
13. Update tests — delete credential_state tests, add HTTP transport tests
14. Run full lint + type + test locally
15. Commit single `feat!:` (phase 3 migration) — NO, use `feat:` per rule. Breaking noted in footer.
16. Push, verify CI green
17. Move to next repo

Do NOT interleave changes across repos. One repo at a time, fully complete before starting next.
