# MCP Core — Unified Transport & Authorization Design

**Date**: 2026-04-10 (v3 2026-04-11)
**Status**: Draft v3 (user corrections applied, awaiting final review)
**Author**: Claude Code session (current)
**Supersedes (partial)**: `2026-04-08-production-hardening-phase2.md` Phase B (OAuth) + Phase C (redefined scope)
**Extends**: `2026-04-05-relay-redesign-and-production-hardening-design.md` (O1-O11 locked)
**Scope**: 12 repos — 7 MCP servers + mcp-core (was mcp-relay-core, will be archived) + claude-plugins + qwen3-embed + web-core + profile
**Companion**: `specs/2026-04-11-doc-update-matrix.md` (file-level doc update matrix)

---

## 1. Context

### 1.1 Audit evidence (verified 2026-04-10/11 qua gh API + git + filesystem)

| Metric | Reality (verified) | Prior session claim |
|--------|-------------------|---------------------|
| Open PRs across 12 repos | **246** | "0" / "453 closed" |
| Open issues | **16** | — |
| Open CodeQL alerts | **15** (10 wet + 3 mnemo + 2 web-core) | "0" |
| Open Dependabot alerts | **2** (wet: langchain-core CVE-2026-40087, cryptography CVE-2026-39892) | — |
| CI pass rate last 20 runs | **~50%** (wet-mcp main branch 0/10) | "100%" |
| better-telegram-mcp merge conflict | **DU http_multi_user.py + 11 M/A files** | "OAuth done" |
| GDrive duplicate folders (rclone lsd) | **mnemo-mcp × 2 (2026-02 + 2026-04), wet-mcp × 2** | "fixed" |
| Human-authored PRs | **1** (OdinYkt telegram #277) | — |
| Commit prefix violations | **~30%** | — |
| Rename impact `mcp-relay-core` → `mcp-core` | **481 refs across 6 repos** (godot 0 refs) | — |
| wet/mnemo/crg embedding backend | **Local auto-detect (ONNX + GGUF per qwen3-embed) + cloud 4 providers (Jina/Gemini/OpenAI/Cohere)** — unified across 3 servers | — |
| mnemo/crg graph backend | **SQLite + sqlite-vec + SQL graph tables** (NOT FalkorDB) | — |
| Claude Code HTTP transport schema | **Verified via ~/.claude backups + better-notion-mcp plugin.json production use** | — |
| Notion HTTP production deployment | **better-notion-mcp/.claude-plugin/plugin.json already uses `"type": "http"` với `https://better-notion-mcp.n24q02m.com/mcp`** | — |
| Credential state gate current implementation | **Inline code gate trong `server.py` của 6 repo + `credential_state.py` (hoặc `.ts`) — NOT a Claude Code PreToolUse hook** | — |
| Pre-existing secrets exposure | **`~/.claude/settings.local.json` + `.claude.json.backup.*` chứa 7 real credentials (GitHub PAT, Gemini, Cohere, Google Stitch, email app passwords × 4 accounts, Telegram API creds)** | — |
| rclone remote state | **`echovault-gdrive:` configured, gcloud 564.0.0 installed (alpha components not installed)** | — |
| Current GDrive scope in sync.py | **wet-mcp/sync.py:44 + mnemo-mcp/sync.py:43 = `drive.file`** — Phase J must update to `drive.appdata` | — |
| OAuth consent screen scope | **Updated to `drive.appdata` by user 2026-04-11** (ahead of code change) | — |

### 1.2 User requirements (locked trong session 2026-04-10/11)

Từ các turn trao đổi của user (bao gồm corrections ngày 2026-04-11):

1. **Best practice, best consolidate** ở mọi quyết định
2. Support multi-OS (Windows/Linux/macOS) + multi-agent (Claude Code, Codex CLI, Copilot, Antigravity, Cursor, Windsurf, OpenCode)
3. Shared MCP core để loại bỏ resource waste (N sessions × heavy ONNX model cho wet/mnemo/crg)
4. Tuân MCP Streamable HTTP 2025-11-25 spec (KHÔNG old HTTP + separate SSE)
5. Drop stdio mode cho mọi server có credentials — chỉ giữ HTTP mode (local hoặc remote)
6. Relay form UX giữ nguyên, nhưng underneath là OAuth 2.1 protocol
7. Self-host capable — cùng codebase, flip config → remote multi-user
8. GDrive single folder invariant — KHÔNG còn duplicate
9. Rule compliance — `fix:`/`feat:` only từ nay, historical commits accept
10. Full/real/live E2E test trước release stable (build local, không release sẵn)
11. CLI subcommands BỎ hoàn toàn — chỉ 1 entry point, management qua MCP tool action (chỉ cho secondary expansion)
12. Cả 3 heavy server (wet + mnemo + crg) đều cần daemon mode
13. `mcp-relay-core` **archive + tạo mcp-core fresh repo** (không rename in-place)
14. Notion exception: local self-hosted AS (paste integration token), remote delegate tới Notion OAuth thật
15. **Remote HTTP bắt buộc chỉ cho telegram/email/notion** (light resources); wet/mnemo/crg default local only, remote opt-in self-host
16. **credential_state.py + inline gate removal** — OAuth 2.1 transport middleware handles credentials, tool code không check nữa
17. **Shared embedding daemon** — build từ đầu, không defer. wet/mnemo/crg gọi chung 1 daemon
18. **Auto-open browser full support** — baseline assumption, remote HTTP mode cũng cần cho claude.ai web client
19. **PSR commit prefix** — đã config xong, không verify lại
20. **Không tạo memory mới cho rule/philosophy** — update profile README + skill ref + CLAUDE.md tại chỗ
21. **Hook migration** — CRG `hooks/hooks.json` PostToolUse hiện dùng stdio subprocess `uvx --from better-code-review-graph python -c ...`, phải đổi sang HTTP POST daemon endpoint

**"Best consolidate" criteria** (định nghĩa cụ thể):

- **Single source of truth**: 1 codebase cho cả local + remote mode, 1 auth path cho 2 flavor, 1 transport implementation cho 7 server
- **Zero duplicate infrastructure**: không separate HTTP + SSE, không separate stdio + HTTP handlers, không per-server auth reimplementation
- **Minimum surface area**: 1 entry point binary per server, 1 code path per operation, 1 encryption scheme
- **Maximum reuse**: chung crypto/transport/auth/lifecycle/install modules qua `mcp-core` library
- **Rollback safety**: archive + rename + migration có thể revert qua git + backup bundle

### 1.3 Prior design constraints (April 5 spec, vẫn locked)

- Relay là primary credential mechanism (qua OAuth 2.1 Authorization page, bản chất là form)
- Env vars chỉ backward compat
- Không có `set_env` MCP action
- No auto-fallback to local ONNX — AWAITING_SETUP blocks **(CHANGED v3)**: credential gate không còn ở tool layer, HTTP 401 thay thế
- Tool queuing via LLM retry

---

## 2. Architectural decisions

### 2.1 Decision: Transport default philosophy — reference existing locations

Triết lý **"Streamable HTTP 2025-11-25 default, stdio fallback proxy only"** được tuyên bố tại các nơi đã tồn tại, spec này KHÔNG duplicate:

| Location | Cập nhật gì |
|----------|-------------|
| `n24q02m/README.md` principle #6 ("Multi-User HTTP Mode") | Mở rộng: "All MCP servers default to Streamable HTTP 2025-11-25 local. stdio exists only as thin proxy for agents without HTTP support. Godot is exception (no credentials)." |
| `n24q02m/skills/fullstack-dev/references/mcp-server.md` | Flip examples line 123+132 từ `"transport": {"type": "stdio"}` sang `"type": "http"`. Update agent compatibility matrix (line 315-324) với Streamable HTTP 2025-11-25 column. Add Streamable HTTP code example as primary, stdio as secondary. |
| `~/.claude/CLAUDE.md` section 3 "E2E TESTING (MCP SERVERS)" | Add HTTP client test path: `httpx.AsyncClient` POST tới `/mcp` endpoint với Bearer token. Giữ stdio_client path làm fallback cho godot. |

Spec §2.1 chỉ cần reference: **"Áp dụng rule từ profile principle #6 + skill mcp-server reference. Không duplicate text ở đây."**

**Exception**: `better-godot-mcp` giữ stdio native — không có credentials, process nhẹ, spawn per-session OK, 0 refs tới `mcp-relay-core` (verified qua grep).

### 2.2 Decision: Auth unification — OAuth 2.1 cho mọi credential server

**Mọi credential server dùng OAuth 2.1 Authorization Server pattern. 2 flavor:**

- **Self-hosted AS**: server tự làm Authorization Server. Authorization page render relay form HTML. User submit credentials → server lưu → issue auth code → client exchange → access token.
- **Delegated AS**: server là OAuth client, redirect `/authorize` tới upstream provider (Notion OAuth). Upstream trả code → server exchange → wrap trong own JWT cho client.

**Mechanism** (changed from v2):

- Tool code KHÔNG còn check credential state (§2.7)
- Transport middleware của `mcp-core` reject request thiếu/expired Bearer token với HTTP 401 + `WWW-Authenticate: Bearer resource_metadata=http://<host>/.well-known/oauth-protected-resource`
- Agent tự động mở browser → OAuth 2.1 dance → token issued → retry (baseline assumption, §2.11 detail)
- Per-session credentials injected vào tool handler qua DI: `credentials: CredStore = Depends(get_session_creds)`

### 2.3 Decision: Local vs Remote mode — 3-tier classification

**Heavy servers (wet/mnemo/crg) — Tier A**: Local HTTP default. Remote = **opt-in self-host only** cho user muốn share cross-machine. Resource consumption (ONNX model ~2GB RAM + SQLite GB-scale DB + embedded SearXNG) không scale multi-user tiện trên VPS nhỏ.

**Light servers (telegram/email/notion) — Tier B**: **Both local HTTP và remote HTTP mandatory**. Remote cần cho agent không connect localhost được (claude.ai web, browser-based agents). Deploy lên `oci-vm-prod` qua CF Tunnel + Caddy (không expose port theo rule "No open ports on VM").

**stdio-only (godot) — Tier C**: No credentials, no HTTP. Giữ nguyên.

| Tier | Bind local | Deploy remote | Credential store local | Credential store remote |
|------|------------|---------------|------------------------|-------------------------|
| A (wet/mnemo/crg) | `127.0.0.1:<port>` | **Opt-in** (self-host, user quyết) | `config.enc` single-user | per-user encrypted multi-user (if self-hosted) |
| B (telegram/email/notion) | `127.0.0.1:<port>` | **Mandatory** (n24q02m infra) | `config.enc` single-user | per-user encrypted multi-user |
| C (godot) | — | — | — | — |

### 2.4 Decision: Server matrix

**"Heavy state"**: resource shared-across-sessions (ONNX model weights, sqlite-vec index, rerank model, DocsDB/memories.db) — loading once saves 500MB-2GB RAM per additional session.

| Server | Tier | Transport | Local auth | Remote auth | Heavy state | Remote prereq |
|--------|:----:|-----------|-----------|-------------|-------------|---------------|
| **wet-mcp** | A | HTTP only | Self-hosted AS | **(opt-in)** Self-hosted AS multi-user | ONNX/GGUF embedding + reranker + DocsDB SQLite 1.5GB + SearXNG subprocess. Embedding model **shared via mcp-embedding-daemon** (§2.11) | Doppler/Infisical master, Caddy + CF Tunnel |
| **mnemo-mcp** | A | HTTP only | Self-hosted AS | **(opt-in)** Self-hosted AS multi-user | ONNX/GGUF embedding + reranker + memories.db SQLite (sqlite-vec + SQL graph tables). Embedding model **shared via mcp-embedding-daemon** | Doppler/Infisical master, Caddy + CF Tunnel |
| **better-code-review-graph** | A | HTTP only | Self-hosted AS | **(opt-in)** Self-hosted AS multi-user | ONNX/GGUF embedding + reranker + graph.db SQLite (sqlite-vec). Embedding model **shared via mcp-embedding-daemon**. Hook `hooks/hooks.json` PostToolUse migrate sang HTTP POST (§2.10) | Doppler/Infisical master, Caddy + CF Tunnel |
| **better-telegram-mcp** | B | HTTP only | Self-hosted AS | **Mandatory** Self-hosted AS multi-user | Per-session Telethon (NOT shared heavy state) | Infisical `29457d18-fd82-4942-9330-7da7982e6b1d` TELEGRAM_API_ID/HASH, Caddy + CF Tunnel |
| **better-email-mcp** | B | HTTP only | Self-hosted AS | **Mandatory** Self-hosted AS multi-user | Per-session IMAP pool (NOT shared heavy state) | Caddy + CF Tunnel, no app-level secret |
| **better-notion-mcp** | B | HTTP only (**already production**) | Self-hosted AS (paste Notion integration token) | **Mandatory** Delegated → Notion OAuth | Per-session Notion client (NOT shared heavy state) | **Notion OAuth app registration** (https://www.notion.so/my-integrations) + client_id/client_secret + redirect_uri whitelist, Caddy + CF Tunnel |
| **better-godot-mcp** | C | stdio only | — | — | Stateless CLI wrapper | n/a |

**Notion notes**:
- `better-notion-mcp/.claude-plugin/plugin.json` đã production với `"type": "http"` + `https://better-notion-mcp.n24q02m.com/mcp`. Đây là reference template cho 5 server khác.
- Local mode dùng self-hosted AS với paste integration token (đơn giản, 1 user)
- Remote mode bắt buộc delegate (mỗi user authorize với Notion account riêng)

### 2.5 Decision: Archive + create new `mcp-core` (không rename in-place)

**Strategy**: Archive `mcp-relay-core` repo + tạo `mcp-core` fresh repo với layout mới.

**Rationale**:
- Scope mới (transport + auth + lifecycle + install + embedding daemon + stdio proxy) lớn hơn scope cũ (credential encryption helper) 10×
- Tên `mcp-core` phản ánh đúng bản chất, không mang gánh "relay" legacy
- Clean semver start (v0.1.0), không inherit v2.0.0 confusion
- Package layout mới thiết kế clean, không phải grep+delete cruft
- CI/CD/Renovate secrets phải reconfig dù chọn phương án nào (cost ngang)

**Migration plan** (xem Phase I plan):

1. Full backup `mcp-relay-core` (git bundle + PR/issue/release export qua `gh api`)
2. Create `mcp-core` repo via `gh repo create n24q02m/mcp-core --public`
3. Scaffold layout mới (xem below)
4. Migrate modules từ old → new theo module mapping
5. Publish `mcp-core` v0.1.0 beta PyPI + NPM
6. Archive `mcp-relay-core` với `gh api -X PATCH repos/n24q02m/mcp-relay-core -f archived=true` + README redirect note

**Layout mới**:

```
mcp-core/
├── packages/core-py/src/mcp_core/
│   ├── transport/
│   │   ├── streamable_http.py    # 2025-11-25 spec base (FastMCP backed)
│   │   └── stdio_proxy.py        # thin stdio→HTTP forwarder
│   ├── auth/
│   │   ├── oauth/
│   │   │   ├── provider.py       # self-hosted OAuth 2.1 AS
│   │   │   ├── delegated.py      # delegated OAuth client (notion)
│   │   │   ├── jwt_issuer.py     # RS256 access token signing
│   │   │   ├── local_ui.py       # relay form HTML renderer
│   │   │   └── remote_ui.py      # full login/consent UI
│   │   ├── user_store/
│   │   │   ├── single_user.py    # config.enc backed
│   │   │   └── multi_user.py     # per-user encrypted PBKDF2 600k
│   │   └── middleware.py         # transport auth middleware (401 + WWW-Authenticate)
│   ├── lifecycle/
│   │   ├── lock.py               # fcntl/msvcrt file lock + PID + port
│   │   └── watchdog.py           # idle shutdown + health
│   ├── crypto/
│   │   ├── config_enc.py         # from mcp_relay_core.config
│   │   ├── session_lock.py       # from mcp_relay_core.session_lock
│   │   └── key_sharing.py        # cross-server key share
│   └── install/
│       ├── agents.py             # detect + write agent config files
│       └── templates/            # .mcp.json, config.toml, mcp.json per agent
├── packages/core-ts/src/mcp_core/
│   └── (mirror TypeScript layout cho email/notion)
├── packages/embedding-daemon/    # §2.11 new
│   └── src/mcp_embedding_daemon/
│       ├── server.py             # FastAPI/FastMCP HTTP server
│       ├── backends/
│       │   ├── onnx.py           # ONNX runtime
│       │   └── gguf.py           # llama-cpp-python
│       └── api.py                # /embed, /rerank endpoints
└── packages/stdio-proxy/         # §2.1 fallback proxy binary
    └── src/mcp_stdio_proxy/
        └── main.py               # forward stdin JSON-RPC → HTTP POST
```

**Module mapping cũ → mới**:

| `mcp_relay_core.*` (Python) | `mcp_core.*` (mới) |
|------------------------------|--------------------|
| `config` | `crypto.config_enc` |
| `session_lock` | `crypto.session_lock` |
| `relay_client` | `auth.oauth.local_ui` (HTML form portion) |
| `crypto` (ECDH) | `crypto.key_sharing` |

| `@n24q02m/mcp-relay-core` (TypeScript) | `@n24q02m/mcp-core` (mới) |
|----------------------------------------|---------------------------|
| tương tự mapping Python | tương tự |

**Base framework**:
- **FastMCP Python** cho `mcp-core` transport (đã implement Streamable HTTP 2025-11-25 + session manager + OAuth middleware hook)
- **@modelcontextprotocol/sdk TypeScript** cho email/notion (đã matching feature set)
- Godot native stdio (không đụng mcp-core)

**Rename impact** (481 refs cần update trong downstream repos, Phase J):

| Repo | Refs | Action |
|------|-----:|--------|
| wet-mcp | ~180 | imports + `pyproject.toml` dep (line 55 + editable path line 120) |
| mnemo-mcp | ~120 | imports + `pyproject.toml` dep |
| better-code-review-graph | ~90 | imports + `pyproject.toml` dep |
| better-telegram-mcp | ~50 | imports + `pyproject.toml` dep |
| better-email-mcp | ~25 | imports + `package.json` dep |
| better-notion-mcp | ~16 | imports + `package.json` dep |
| better-godot-mcp | **0** | No change |
| **Total** | **481** | Automated sed + verification grep |

### 2.6 Decision: GDrive fix — drive.appdata scope + manual web console + rclone cleanup

**Current state**:
- User **đã update consent screen scope sang `drive.appdata`** (2026-04-11, manual web console action). Verified via user confirmation.
- Code vẫn ở `drive.file`: `wet-mcp/src/wet_mcp/sync.py:44`, `mnemo-mcp/src/mnemo_mcp/sync.py:43`.
- GDrive still has duplicate folders: `mnemo-mcp × 2` (Feb + Apr), `wet-mcp × 2` (Feb + Apr) — verified via `rclone lsd echovault-gdrive:`

**Work split**:

| Ai | Việc | Tool |
|----|------|------|
| Em | Update `_SCOPE = "https://www.googleapis.com/auth/drive.appdata"` trong 2 sync.py | Edit tool |
| Em | Replace `_find_or_create_folder()` logic với `appDataFolder` well-known ID | Edit tool |
| Em | rclone list + download + SQLite analyze + merge duplicate folders (Phase H) | rclone CLI + sqlite3 Python |
| **User** (đã xong) | Web console: add `drive.appdata` scope vào OAuth consent screen | https://console.cloud.google.com/apis/credentials/consent |
| **User** (sau Phase J deploy) | OAuth re-consent lần đầu với new scope | Browser |

**rclone cleanup — SQLite-aware merge (Phase H, với user in loop)**:

1. List both folder IDs cho mỗi server pair
2. Download cả 2 DB về `./_backup/gdrive-audit/<server>-<folder_id>/`
3. sqlite3 schema analysis + row count + max timestamp per table
4. Merge decision: **`INSERT OR IGNORE` merge** nếu schema identical + no ID conflict; **schema migration + merge** nếu schema drift; **hỏi user case-by-case** nếu conflict IDs
5. Upload merged DB tới canonical folder (sẽ migrate to appdata sau Phase J)
6. `rclone purge` duplicate folder kia
7. Verify `rclone lsd` chỉ còn 1 folder per server

**Migration to appdata** (after Phase J code deploys):
- First run post-upgrade: code detect old folder, upload files to `appDataFolder` via new scope, flag migrated
- User re-consent once
- Old folder rồi cũng xoá được

### 2.7 Decision: CLI removal + credential_state gate removal

**(a) CLI removal**: 1 entry point per server. Mode detection trong binary:

- `MCP_CORE_MODE=server` env OR spawned bởi stdio proxy launcher OR file lock indicates server role → HTTP server mode
- stdin là pipe từ agent stdio client (default) → stdio proxy mode + auto-ensure HTTP server qua lifecycle lock
- Race: fcntl.flock Unix / msvcrt.locking Windows atomic create + retry

**(b) credential_state.py removal** (new v3):

Xoá hoàn toàn `credential_state.py` (hoặc `.ts`) + inline AWAITING_SETUP gate trong 6 repo. OAuth 2.1 transport middleware handle credential check. Tool code giả định credentials present.

**Files cần xoá**:

| Repo | File xoá | Files sửa |
|------|----------|-----------|
| wet-mcp | `src/wet_mcp/credential_state.py`, `tests/test_credential_state.py` | `src/wet_mcp/server.py` (bỏ AWAITING_SETUP block line 58-70, 146, 251-333, 1278-1395), `setup_tool.py` (bỏ `trigger_relay_setup`) |
| mnemo-mcp | `src/mnemo_mcp/credential_state.py`, `tests/test_credential_state.py` | `src/mnemo_mcp/server.py`, `setup_tool.py`, `tests/test_server_setup_actions.py` |
| better-code-review-graph | `src/better_code_review_graph/credential_state.py`, `tests/test_credential_state.py`, `tests/test_setup_tool.py` | `src/better_code_review_graph/server.py` |
| better-telegram-mcp | `src/better_telegram_mcp/credential_state.py`, `tests/test_credential_state.py`, `tests/test_relay_setup.py` | `src/better_telegram_mcp/server.py`, `tests/test_server.py` |
| better-email-mcp | `src/credential-state.ts`, `src/credential-state.test.ts`, `build/src/credential-state.d.ts` | `src/init-server.ts`, `src/tools/composite/setup.ts`, `src/tools/registry.ts`, `init-server.test.ts`, `setup.test.ts` |
| better-notion-mcp | `src/credential-state.ts`, `build/src/credential-state.d.ts` | `src/init-server.ts`, `src/tools/registry.ts`, `src/transports/stdio.ts`, tests |

**Replacement**: `mcp_core.auth.middleware` global middleware áp vào Streamable HTTP app. Per-session credentials inject qua `Depends(get_session_creds)` trong FastMCP tool handlers.

**(c) Management actions** — **secondary utility only, không phải primary install path**:

Primary install vẫn theo marketplace pattern hiện có (`/plugin install wet-mcp@n24q02m-plugins`) hoặc manual qua `setup-with-agent.md` / `setup-manual.md` updated docs. MCP tool actions là **secondary** cho cross-agent propagation sau khi đã bootstrap 1 agent:

- `<server>(action="status")` — health, port, sessions, memory, uptime
- `<server>(action="install_agent", targets=[...])` — ghi config files cho agents khác
- `<server>(action="uninstall_agent", targets=[...])` — cleanup
- `<server>(action="reset_credentials")` — clear config.enc, trigger new OAuth dance
- `<server>(action="shutdown_daemon")` — clean exit HTTP server
- `<server>(action="trigger_relay")` — returns authorization URL, force open browser

### 2.8 Decision: Agent config auto-write

**Tier 1 (primary, must work)**:

| Agent | Config file | Entry format |
|-------|-------------|-------------|
| Claude Code | `~/.claude/settings.json` hoặc `{project}/.mcp.json` | `{"type": "http", "url": "http://127.0.0.1:<port>/mcp", "headers": {"Authorization": "Bearer <token>"}}` |
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.<name>]` với `url`, `bearer_token_env_var` |
| GitHub Copilot (VSCode Insiders) | `{project}/.vscode/mcp.json` hoặc `~/AppData/Roaming/Code - Insiders/User/mcp.json` | `{"servers": {"<name>": {"type": "http", "url": "..."}}}` |

**Tier 2 (secondary, best-effort)**:

| Agent | Config file |
|-------|-------------|
| Antigravity (Gemini CLI) | `~/.gemini/antigravity/mcp_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp.json` |
| OpenCode | `~/.config/opencode/opencode.json` |

Merge logic: preserve existing entries, add/update cho server hiện tại, write back với `.bak`.

### 2.9 Decision: Commit prefix enforcement

- Pre-commit hook trong 12 repos: regex `^(fix|feat)(\([a-z0-9-]+\))?:` — reject khác
- Breaking change: footer `BREAKING CHANGE: <description>`, KHÔNG `!` indicator
- PSR config **đã updated** (per user 2026-04-11), không verify lại
- Renovate config override: prefix `fix(deps):` — cần verify trong Phase K nếu chưa
- Historical bad commits: accept as-is

### 2.10 Decision: Hook migration (CRG only)

**Current state** (verified `better-code-review-graph/hooks/hooks.json`):

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh" }] }],
    "PostToolUse": [{
      "matcher": "Write|Edit|Bash",
      "hooks": [{
        "type": "command",
        "command": "uvx --from better-code-review-graph python -c \"from better_code_review_graph.incremental import incremental_update_from_hook; incremental_update_from_hook()\" 2>/dev/null || true"
      }]
    }]
  }
}
```

**Problem**: `PostToolUse` spawn uvx subprocess **mỗi lần** Write/Edit/Bash → load ONNX model lại → RAM spike + latency. Pattern này thiết kế cho stdio era.

**Fix** (Phase J CRG):

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh" }] }],
    "PostToolUse": [{
      "matcher": "Write|Edit|Bash",
      "hooks": [{
        "type": "command",
        "command": "curl -sS -X POST http://127.0.0.1:<crg_port>/internal/incremental-update -H 'Authorization: Bearer '${MCP_CORE_TOKEN} -H 'Content-Type: application/json' -d '{\"tool\":\"${CLAUDE_TOOL_NAME}\",\"files\":${CLAUDE_TOOL_FILES}}' 2>/dev/null || true"
      }]
    }]
  }
}
```

HTTP POST tới running CRG daemon endpoint thay vì spawn fresh subprocess. Daemon đã load model — incremental update chạy nhanh hơn 10-100x.

`session-start.sh` cũng review — có thể đơn giản hoá nếu nó cũng gọi uvx.

**Other repos**: wet/mnemo/telegram/email/notion chưa có `hooks/hooks.json` — không cần migrate.

### 2.11 Decision: Shared embedding daemon (new in v3)

**Component**: `mcp-embedding-daemon` — standalone process trong `mcp-core/packages/embedding-daemon/`, load model 1 lần, serve wet/mnemo/crg qua localhost HTTP.

**API**:

- `POST /embed` → `{"model": "qwen3-0.6b", "input": ["text1", "text2"], "dims": 768}` → `{"data": [[0.1,...], ...]}`
- `POST /rerank` → `{"model": "qwen3-rerank-0.6b", "query": "...", "documents": [...]}` → `{"results": [{"index": 0, "score": 0.95}, ...]}`
- `GET /health` → `{"status": "ok", "model_loaded": true, "backend": "onnx" | "gguf", "memory_mb": 1850}`
- `GET /.well-known/oauth-protected-resource` → OAuth metadata (cùng pattern với các server khác)

**Backend auto-detect** (reuse qwen3-embed repo logic):
- CUDA available + model.onnx + weights → ONNX with CUDAExecutionProvider
- CPU only + quantized GGUF → llama-cpp-python
- Cloud mode: daemon pass-through tới Jina/Gemini/OpenAI/Cohere (4 providers) — tránh mỗi server tự quản 4 API keys

**Bootstrap**:
- wet/mnemo/crg khởi động → detect `MCP_EMBEDDING_DAEMON_URL` env → nếu set → client mode (HTTP call). Nếu không set → fallback spawn daemon qua lifecycle lock (tương tự stdio proxy auto-ensure)
- Default: daemon tự spawn lần đầu server nào đó cần embedding, các server sau share

**Resource save**: 3 × 2GB ONNX = 6GB → 1 × 2GB = 2GB (4GB RAM saved)

**Client side** trong wet/mnemo/crg: thay code load model trực tiếp bằng `mcp_core.embedding.Client(daemon_url)`. Logic fallback Cloud → Local vẫn ở client, daemon chỉ là transport.

---

## 3. Security considerations

### 3.1 Local mode (Tier A + Tier B local)

- Bind strictly `127.0.0.1`, không `0.0.0.0` kể cả loopback (tránh Windows Firewall prompt)
- Bearer token file 0600 (Unix) / NTFS ACL current user only (Windows)
- `Origin` header validation: accept `http://127.0.0.1:*` + `http://localhost:*`, reject khác 403
- DNS rebinding defense: reject `Host` header không phải `127.0.0.1|localhost|::1`
- JWT signing key sinh lần đầu, persist trong config.enc, rotation qua `reset_credentials` action

### 3.2 Remote mode (Tier B mandatory, Tier A opt-in)

- Bind `0.0.0.0` phía sau Caddy + TLS + CF Tunnel HOẶC Tailscale (rule "No open ports on VM")
- OAuth 2.1 với PKCE mandatory
- Per-user credential encryption: PBKDF2 600k iterations + user_id + master secret
- Master secret trong Doppler (VM config) + Infisical (app secrets)
- Rate limiting per user (token bucket) qua middleware
- Audit log: authorize/token/revoke events
- Multi-user isolation fuzz test Phase L

**Infisical structure** (`mcp-core-prod` project, production environment):

```
/mcp-core/
  MASTER_SECRET          # base64 32 bytes, PBKDF2 input
  JWT_PRIVATE_KEY_PEM    # RS256 signing key
  JWT_PUBLIC_KEY_PEM
/wet-mcp/                # (opt-in remote only — skip nếu không self-host)
  GDRIVE_OAUTH_CLIENT_ID
  GDRIVE_OAUTH_CLIENT_SECRET
  SEARXNG_CONFIG
/mnemo-mcp/              # (opt-in remote only)
  GDRIVE_OAUTH_CLIENT_ID
  GDRIVE_OAUTH_CLIENT_SECRET
/better-code-review-graph/  # (opt-in remote only)
  GITHUB_APP_PRIVATE_KEY
  GITHUB_APP_CLIENT_ID
/better-telegram-mcp/    # (mandatory — existing Infisical project 29457d18-fd82-4942-9330-7da7982e6b1d)
  TELEGRAM_API_ID
  TELEGRAM_API_HASH
/better-email-mcp/
  (no app-level secret)
/better-notion-mcp/
  NOTION_OAUTH_CLIENT_ID
  NOTION_OAUTH_CLIENT_SECRET
  NOTION_OAUTH_REDIRECT_URI
```

Universal-auth machine identity (Client ID `92ae6217-...`) fetches secrets via `infisical export --format=dotenv --token=$INFISICAL_TOKEN`.

### 3.3 Credential flow

- Credentials KHÔNG qua LLM chat context
- OAuth 2.1 authorization page (relay form HTML) nhận credentials, server process immediately, store encrypted
- No `set_env` MCP action anywhere
- Token exchange theo OAuth 2.1 standard

### 3.4 Pre-existing secret exposure (out of scope, flagged)

`~/.claude/settings.local.json` + `~/.claude/backups/.claude.json.*` chứa 7 real credentials hardcoded. **Fix ownership không thuộc 12 repo này** nhưng user cần:

1. Rotate GitHub PAT, Gemini, Cohere, Google Stitch, email app passwords × 4, Telegram API creds
2. Migrate `settings.local.json` sang Infisical fetch-at-runtime
3. Sanitize backup files trước khi sync bất cứ đâu

**Enforce going forward**: MCP core credential load luôn qua Infisical, không qua env vars user set.

---

## 4. Backward compatibility & migration

### 4.1 Breaking changes

- **mcp-relay-core archived → mcp-core fresh repo**: import path change, package name change, NPM/PyPI package name change (`mcp-relay-core` → `mcp-core`)
- **stdio mode removed** cho 6 credential server: major version bump per server
- **credential_state.py removed** cho 6 repos: tool behavior change (no more AWAITING_SETUP inline error, now HTTP 401)
- **GDrive scope** `drive.file` → `drive.appdata`: user re-consent 1 lần
- **CRG hooks.json PostToolUse** stdio subprocess → HTTP POST

### 4.2 Migration path

- Release current N.x.y: unchanged
- Release N+1.0.0: tất cả breaking changes aggregated (không grace period vì chưa external user đáng kể)
- Data migration routine first run post-upgrade (GDrive appdata, optional backup old config.enc)

### 4.3 User migration tool

- `<server>(action="install_agent", targets=["all"])` detect existing stdio entries, replace HTTP
- Existing `config.enc` format compatible — AES-GCM machine key scheme không đổi
- GDrive: `reset_credentials` triggers re-consent với new scope

---

## 5. Verification strategy

### 5.1 Evidence requirement

Mọi task complete claim PHẢI kèm:
- `gh api` / `gh pr view` / `gh run view` output
- `git log --oneline` với hash
- File path + line number
- Test output (command + stdout)

### 5.2 Phase gate acceptance

Mỗi phase acceptance criteria cụ thể (xem plan files). Phase kế chỉ start sau evidence pass.

### 5.3 E2E gate trước release

Release stable CHỈ sau Phase M E2E suite pass 100% với **local unreleased build** (không dùng released package).

---

## 6. Risk analysis & rollback

| Risk | Likelihood | Impact | Mitigation | Rollback |
|------|:---:|:---:|------------|----------|
| Archive mcp-relay-core + create new breaks 3 downstream editable paths | High | Medium | Same-commit update of all 3 `pyproject.toml` editable paths; verify `uv sync` before push | git bundle restore + `gh api unarchive`; re-activate editable paths |
| FastMCP base framework incompatible với existing mcp-relay-core APIs | Medium | High | Spike FastMCP trong Phase I4 với 1 server (wet-mcp) trước khi roll mnemo + crg | Keep legacy Starlette custom transport code path in `mcp_core.transport.legacy.py`, flip flag per server |
| GDrive appdata migration corrupts SQLite DBs | Low | High | Upload appdata **first**, verify checksum, only then delete old folders; keep rclone + local backup before destructive op | rclone restore từ local backup trong 24h |
| Duplicate GDrive folders contain divergent data (SQLite merge conflict) | High | Medium | Phase H interactive merge with user; sqlite3 diff analysis before decision | Keep both folders with suffix, defer final merge |
| OAuth 2.1 auto-browser UX broken in some agent | High | Medium | Baseline assumption documented in profile + skill ref; fallback: print URL stderr; Phase G5 empirical (reduced scope) | Per-agent compat matrix; revert specific agent to legacy trigger if needed |
| Pre-commit prefix hook blocks urgent fix PR | Medium | Low | Hook only on push; bypass discouraged | Remove hook commit, push fix, re-add |
| Multi-user remote leaks User A creds to User B | Low | Critical | Phase L fuzz test 10 concurrent users | Kill remote, force local, rotate master |
| Notion OAuth app registration delays remote launch | High | Low | Register Notion OAuth app before Phase K; local unaffected | Remote notion stays down; other 5 remote servers unaffected |
| credential_state.py removal breaks test suite across 6 repos | High | Medium | Phase J update test suite simultaneously với removal; baseline test run before-after | Restore file + re-add inline gate temporarily |
| Shared embedding daemon single point of failure | Medium | Medium | Auto-restart via lifecycle lock; fallback: each server loads own model if daemon down | Revert to per-server loading (spec §2.11 fallback path) |
| CRG `hooks.json` HTTP POST fails silently (daemon not running) | Medium | Low | `|| true` at end of curl command; stderr log | No rollback needed, hook is best-effort |

### 6.2 PR review SLA

**246 open PRs** aggressive strategy:
- Bot PRs (Renovate, Dependabot): batch review + merge trong Phase G nếu CI xanh + không touch auth/transport
- Human PRs (1 only: OdinYkt telegram #277): individual review với Phase 3 context; possibly close with explanation nếu conflict
- SLA: Phase G kết thúc ≤ 50 open PRs

### 6.3 Test credential strategy

E2E test cần real credentials cho mọi server. Strategy:
- Dedicated test accounts (test Telegram, test Notion workspace, test Gmail app password, test GitHub App)
- Stored trong Infisical `mcp-core-test` project (separate env)
- Rotated monthly
- CI fetches via machine identity

### 6.4 Circular dependency check

`mcp-core` depends on `web-core` cho HTTP client utilities. `web-core` KHÔNG import `mcp-core`. Verify trong Phase I3 dependency graph check.

---

## 7. Open design questions

1. **Shared ONNX daemon startup race**: 2 agent spawn song song → cả 2 cố spawn embedding daemon → conflict. Resolve: atomic file lock + retry (Phase I7).
2. **Idle shutdown policy**: default local HTTP server idle bao lâu exit? Recommend: never shutdown, configurable `MCP_CORE_IDLE_TIMEOUT=<minutes>`.
3. **Notion SDK current Streamable HTTP version**: verify Phase G6 vì `better-notion-mcp` đã production HTTP nhưng SDK version có thể chưa 2025-11-25.

**Resolved / removed** (v3):
- ~~Agent auto-browser reliability~~ → baseline assumption, không test empirical
- ~~PSR commit prefix config~~ → user confirmed đã xong

---

## 8. Objectives mapping (O12-O19)

- **O12** — Unblock CI: 12 repo CI xanh 3 run liên tiếp ubuntu + windows + macos
- **O13** — GDrive single-folder: wet + mnemo sync vào 1 appdata folder, token rotation không duplicate
- **O14** — Streamable HTTP 2025-11-25 compliance: mcp-core + 6 credential server dùng unified `/mcp` endpoint
- **O15** — Unified OAuth 2.1: self-hosted AS cho 5 server, delegated cho notion remote
- **O16** — Resource consolidation: wet + mnemo + crg chạy long-running HTTP + shared embedding daemon
- **O17** — Multi-OS + multi-agent: 12 repo CI matrix pass, `install_agent` ghi config đúng cho 7 agent
- **O18** — Docs/rules compliance: README accurate, profile accurate, pre-commit enforce `fix:`/`feat:` từ 2026-04-10
- **O19** — Full/real/live E2E test pre-release: clean state, real credentials, build local, mọi action/mode × server × concurrent session

---

## 9. References

- MCP Streamable HTTP 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- OAuth 2.1: RFC 9470
- Google Drive API appdata: https://developers.google.com/drive/api/guides/appdata
- FastMCP Streamable HTTP: https://gofastmcp.com/deployment/http
- **Profile principles**: `n24q02m/README.md` §"Design Philosophy" principle #6
- **Skill reference**: `n24q02m/skills/fullstack-dev/references/mcp-server.md`
- **Global rules**: `~/.claude/CLAUDE.md` §3 E2E TESTING
- **Doc update matrix**: `specs/2026-04-11-doc-update-matrix.md` (companion)
- Prior spec: `specs/2026-04-05-relay-redesign-and-production-hardening-design.md`
- Prior plan: `plans/2026-04-08-production-hardening-phase2.md`
