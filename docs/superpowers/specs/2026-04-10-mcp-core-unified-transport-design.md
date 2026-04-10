# MCP Core — Unified Transport & Authorization Design

**Date**: 2026-04-10
**Status**: Draft for review
**Author**: Claude Code session (current)
**Supersedes (partial)**: `2026-04-08-production-hardening-phase2.md` Phase B (OAuth) + Phase C (redefined scope)
**Extends**: `2026-04-05-relay-redesign-and-production-hardening-design.md` (O1-O11 locked)
**Scope**: 12 repos — 7 MCP servers + mcp-core (was mcp-relay-core) + claude-plugins + qwen3-embed + web-core + profile

---

## 1. Context

### 1.1 Audit evidence (verified 2026-04-10 qua gh API + git + filesystem)

| Metric | Reality (verified) | Prior session claim (hallucinated) |
|--------|-------------------|-----------------------------------|
| Open PRs across 12 repos | **246** | "0" (Antigravity), "453 closed" (cf5ac4a3) |
| Open issues | **16** | — |
| Open CodeQL alerts | **15** (10 wet, 3 mnemo, 2 web-core) | "0" (Antigravity) |
| Open Dependabot alerts | **2** (wet: langchain-core, cryptography) | — |
| CI pass rate last 20 runs | **~50%** (wet-mcp worst: 0/10) | "100%" (Antigravity) |
| better-telegram-mcp merge conflict | **12 dirty files, DU http_multi_user.py** | "OAuth done" (Antigravity) |
| GDrive duplicate folders | **4.5 GB wasted, fresh duplicates Apr 10 22:10** | "fixed" (session 3a19aecd) |
| Human-authored PRs | **1** (OdinYkt telegram #277) | — |
| Commit prefix violations | **~30% across repos** | — |

### 1.2 User requirements (locked trong session 2026-04-10)

Từ các turn trao đổi của user:

1. Best practice, best consolidate ở mọi quyết định
2. Support multi-OS (Windows/Linux/macOS) + multi-agent (Claude Code, Codex CLI, Copilot, Antigravity, Cursor, OpenCode)
3. Shared MCP core để loại bỏ resource waste (N sessions × heavy ONNX model cho wet/mnemo/crg)
4. Tuân MCP Streamable HTTP 2025-11-25 spec (KHÔNG old HTTP + separate SSE)
5. Drop stdio mode cho mọi server có credentials — chỉ giữ HTTP mode (local hoặc remote)
6. Relay form UX giữ nguyên, nhưng underneath là OAuth 2.1 protocol (agent tự động mở browser khi 401)
7. Self-host capable — cùng codebase, flip config → remote multi-user
8. GDrive single folder invariant — KHÔNG còn duplicate
9. Rule compliance — `fix:`/`feat:` only từ nay, historical commits accept
10. Full/real/live E2E test trước release stable (build local, không release sẵn)
11. CLI subcommands BỎ hoàn toàn — chỉ 1 entry point, management qua MCP tool action
12. Cả 3 heavy server (wet + mnemo + crg) đều cần daemon mode (không phải chỉ wet)
13. `mcp-relay-core` rename → `mcp-core` (scope mở rộng)
14. Notion exception: local dùng self-hosted AS (relay form), remote delegate tới Notion OAuth thật

### 1.3 Prior design constraints (April 5 spec, vẫn locked)

- Relay là primary credential mechanism
- Env vars chỉ backward compat
- Không có `set_env` MCP action
- No auto-fallback to local ONNX — AWAITING_SETUP blocks, not degrade
- Hook-based credential check
- Tool queuing via LLM retry

---

## 2. Architectural decisions

### 2.1 Decision: Transport unification — Streamable HTTP 2025-11-25 only

**Bỏ stdio mode hoàn toàn cho mọi server có credentials. Chỉ giữ Streamable HTTP transport.**

**Rationale**:
- Spec 2025-11-25 định nghĩa Streamable HTTP là canonical transport
- 1 endpoint `/mcp` duy nhất (POST + GET + DELETE) thay vì HTTP + separate `/sse`
- stdio phức tạp (EOF, subprocess lifecycle, separate relay trigger)
- Multi-session trên 1 process (key lợi ích cho heavy servers)
- Session isolation qua `Mcp-Session-Id` header native từ spec

**Exception**: `better-godot-mcp` giữ stdio — không có credentials, process nhẹ, spawn per-session OK.

**Backward compat cho stdio-only agents**: thin `stdio_proxy` binary trong mcp-core forward JSON-RPC frames từ stdin → HTTP POST → response → stdout. Không phải server, chỉ adapter.

### 2.2 Decision: Auth unification — OAuth 2.1 cho mọi credential server

**Mọi credential server dùng OAuth 2.1 Authorization Server pattern. 2 flavor:**

- **Self-hosted AS**: server tự làm Authorization Server. Authorization page render relay form HTML. User paste credentials → submit → server lưu → issue auth code → client exchange → access token.
- **Delegated AS**: server là OAuth client, redirect `/authorize` tới upstream provider (Notion OAuth). Upstream trả code → server exchange với upstream → wrap trong own JWT cho client.

**Rationale**:
- Spec 2025-11-25 requires OAuth 2.1 (RFC 9470)
- Client tự động handle 401 → `WWW-Authenticate: Bearer resource_metadata=...` → open browser → retry → UX cải thiện so với hiện tại (user không phải copy URL thủ công)
- 1 auth code path trong `mcp_core.auth.oauth` — reuse across mọi server mọi mode
- Security standards compliance (PKCE, DCR, token rotation)

### 2.3 Decision: Local vs Remote mode

| Mode | Bind | Credential store | User scope | Default |
|------|------|-----------------|-----------|---------|
| **Local HTTP** | `127.0.0.1:<port>` | `config.enc` single-user | 1 user (local machine) | Yes |
| **Remote HTTP** | `0.0.0.0` (hoặc tunnel) | per-user encrypted store | Multi-user always | Opt-in |

- Mặc định: Local mode (single-user).
- Self-host: flip config flag `MCP_CORE_MODE=remote`, thêm reverse proxy, OAuth full login/consent flow.
- Remote mode **luôn** hỗ trợ multi-user — single-user remote là degenerate case (N=1), không code path riêng.
- Server CÙNG codebase, cùng Streamable HTTP transport, chỉ khác auth middleware + credential store backend.

### 2.4 Decision: Server matrix

| Server | Transport | Local auth | Remote auth | Heavy state (shared across sessions) |
|--------|-----------|-----------|-------------|--------------------------------------|
| **wet-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | ONNX embedding + reranker + DocsDB SQLite 1.5GB + SearXNG subprocess |
| **mnemo-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | ONNX embedding + reranker + memories.db SQLite (with sqlite-vec + graph tables) |
| **better-code-review-graph** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | ONNX embedding + reranker + graph.db SQLite (with sqlite-vec) |
| **better-telegram-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | Per-session Telethon (not shared) |
| **better-email-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | Per-session IMAP pool (not shared) |
| **better-notion-mcp** | HTTP only | **Self-hosted AS** (paste Notion integration token) | **Delegated → Notion OAuth** | Per-session Notion client (not shared) |
| **better-godot-mcp** | stdio only | — | — | Stateless CLI wrapper |

**Notion exception explanation**: Notion có real OAuth provider cho multi-user (`api.notion.com/v1/oauth`). Remote mode bắt buộc delegate để mỗi user authorize với chính Notion account của họ. Local mode vẫn dùng self-hosted AS với relay form paste integration token (đơn giản, không cần OAuth dance cho 1 user).

### 2.5 Decision: mcp-core package (renamed from mcp-relay-core)

**Rename `mcp-relay-core` → `mcp-core`. Mở rộng scope.**

**Layout mới**:

```
mcp-core/
├── packages/core-py/src/mcp_core/
│   ├── transport/
│   │   ├── streamable_http.py    # 2025-11-25 spec base server
│   │   └── stdio_proxy.py        # thin stdio to HTTP forwarder
│   ├── auth/
│   │   ├── oauth/
│   │   │   ├── provider.py       # self-hosted OAuth 2.1 AS
│   │   │   ├── delegated.py      # delegated OAuth client (for notion)
│   │   │   ├── jwt_issuer.py     # access token signing (RS256)
│   │   │   ├── local_ui.py       # relay form HTML renderer
│   │   │   └── remote_ui.py      # full login/consent UI
│   │   ├── user_store/
│   │   │   ├── single_user.py    # config.enc backed (local mode)
│   │   │   └── multi_user.py     # per-user encrypted (remote mode)
│   │   └── middleware.py         # transport auth middleware
│   ├── lifecycle/
│   │   ├── lock.py               # PID + port file lock
│   │   └── watchdog.py           # idle shutdown + health
│   ├── crypto/
│   │   ├── config_enc.py         # AES-GCM machine-key (from old mcp_relay_core.config)
│   │   ├── session_lock.py       # from old mcp_relay_core.session_lock
│   │   └── key_sharing.py        # cross-server key share
│   └── install/
│       ├── agents.py             # detect + write agent config files
│       └── templates/            # .mcp.json, config.toml, mcp.json per agent
└── packages/core-ts/src/mcp_core/
    └── (same structure, TypeScript for email/notion/godot)
```

**Module mapping**: tất cả module của `mcp_relay_core` chuyển thành submodule của `mcp_core.crypto` + `mcp_core.auth.oauth.local_ui`. Không có logic nào bị lost, chỉ reorganize.

### 2.6 Decision: GDrive fix — drive.appdata scope

**wet-mcp + mnemo-mcp chuyển scope từ `drive.file` sang `drive.appdata`.**

**Rationale**:
- `drive.appdata` là scope Google thiết kế riêng cho "app config/data that user doesn't interact with directly"
- Zero duplicate by architectural design (1 appdata folder per user per OAuth client_id, persistent across tokens)
- Minimum scope (hẹp nhất trong Drive scopes)
- Không cần `permissions.create` workaround
- Không cần manual folder ID
- Data vẫn private của user (trong their drive nhưng không hiện Drive UI)

**Trade-off**: User không browse `docs.db` / `memories.db` trực tiếp. Không phải vấn đề vì không ai mở 1.5GB SQLite file thủ công.

**Migration**: one-time routine first run after upgrade — detect files trong old folders, upload to appdata, flag migrated. User re-consent OAuth 1 lần.

**Cleanup**: `rclone delete` old `wet-mcp (2)/`, `mnemo-mcp (1)/`, stale DB files (destructive, confirm trước khi chạy).

### 2.7 Decision: CLI removal

**KHÔNG có CLI subcommand. Chỉ 1 entry point per server.**

**Mode detection trong entry point binary**:
- Nếu env `MCP_CORE_MODE=server` HOẶC được spawn bởi stdio proxy launcher HOẶC file lock indicates server role → chạy HTTP server
- Nếu stdin là pipe từ agent stdio client (default) → chạy stdio proxy + auto-ensure HTTP server qua lifecycle lock
- Race condition: 2 agents start cùng lúc → file lock với atomic create + retry

**Management qua MCP tool action** (mở rộng mega-tool hiện có):
- `wet(action="status")` — server health, port, connected sessions, memory usage, uptime
- `wet(action="install_agent", targets=["claude_code", "codex", "copilot", "antigravity", "cursor", "opencode"])` — auto detect và write config files
- `wet(action="uninstall_agent", targets=[...])` — cleanup
- `wet(action="reset_credentials")` — trigger relay form re-submission, clear config.enc

### 2.8 Decision: Agent config auto-write

**`mcp_core.install.agents` module support**:

| Agent | Config file | Entry format |
|-------|-------------|-------------|
| Claude Code | `~/.claude/settings.json` hoặc `{project}/.mcp.json` | `{"type": "http", "url": "http://127.0.0.1:<port>/mcp", "headers": {"Authorization": "Bearer <token>"}}` |
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.<name>]` với `url`, `bearer_token_env_var` |
| GitHub Copilot (VSCode) | `{project}/.vscode/mcp.json` hoặc `~/AppData/Roaming/Code/User/mcp.json` | `{"servers": {"<name>": {"type": "http", "url": "..."}}}` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` | tương tự Claude Code |
| Cursor | `~/.cursor/mcp.json` | tương tự Claude Code |
| Windsurf | `~/.codeium/windsurf/mcp.json` | tương tự |
| OpenCode | `~/.config/opencode/opencode.json` (MCP section) | tương tự |

Merge logic: preserve existing entries, add/update entry cho server hiện tại, write back với backup.

### 2.9 Decision: Commit prefix enforcement

- Pre-commit hook trong 12 repos: regex `^(fix|feat)(\([a-z0-9-]+\))?:` — reject mọi prefix khác
- Breaking change: dùng footer `BREAKING CHANGE: <description>` trong body, KHÔNG `!` indicator
- PSR config update: release commit template từ `chore(release): vX.Y.Z` sang `fix(release): vX.Y.Z`
- Renovate config override: commit message prefix từ `chore(deps):` sang `fix(deps):`
- Bot PR (Bolt/Sentinel/Palette): nếu tools hỗ trợ config prefix, update template. Nếu không, pre-commit hook reject → user/admin manually rename message
- Historical bad commits: accept as-is, không force-rewrite history

---

## 3. Security considerations

### 3.1 Local mode

- Bind strictly `127.0.0.1` (không `0.0.0.0` kể cả loopback) để tránh Windows Firewall prompt
- Bearer token file 0600 (Unix) / NTFS ACL current user only (Windows)
- `Origin` header validation: accept `http://127.0.0.1:*` và `http://localhost:*`, reject others với 403
- DNS rebinding defense: reject `Host` header không phải `127.0.0.1`, `localhost`, `::1`
- JWT signing key sinh ra lần đầu server start, persisted trong config.enc, rotation qua `reset_credentials` action

### 3.2 Remote mode

- Bind `0.0.0.0` nhưng phía trước phải có Caddy reverse proxy + TLS + CF Tunnel hoặc Tailscale (tuân rule "No open ports on VM")
- OAuth 2.1 với PKCE mandatory
- Per-user credential encryption: PBKDF2 600k iterations + user_id + master secret
- Master secret trong Doppler/Infisical, rotation procedure documented per server repo AGENTS.md
- Rate limiting per user (token bucket) qua middleware
- Audit log: mọi authorize/token/revoke event
- Multi-user isolation test: user A không decrypt được user B credentials

### 3.3 Credential flow (không đổi)

- Credentials KHÔNG bao giờ pass qua LLM chat context
- Relay form POST body nhận credentials, server process immediately, store encrypted
- No `set_env` MCP action anywhere
- Token exchange theo OAuth 2.1 standard

---

## 4. Backward compatibility & migration

### 4.1 Breaking changes

- **mcp-relay-core → mcp-core**: import path change, major version bump (v2.0.0)
- **stdio mode drop** cho 6 credential servers: major version bump per server
- **Old HTTP relay endpoints** (`/sse`, `/events/*`): bỏ hoàn toàn, không grace period (chưa có external user ngoài 1 PR contributor)
- **GDrive scope** `drive.file` → `drive.appdata`: user phải re-consent OAuth 1 lần

### 4.2 Migration path cho user

- Release current N.x.y: unchanged, no action needed
- Release N+1.0.0: stdio mode deprecation warning printed to stderr khi chạy stdio mode, default vẫn stdio nhưng encourage switching
- Release N+2.0.0: stdio mode removed hoàn toàn, chỉ HTTP mode

Tuy nhiên vì repo ecosystem này chưa có external user, có thể skip grace period và release N+1.0.0 thẳng với stdio removed.

### 4.3 User migration tool

- `wet(action="install_agent", targets=["all"])` detect existing stdio entries trong agent config files, replace với HTTP entries
- Existing `config.enc` format compatible — AES-GCM machine key scheme không đổi

---

## 5. Verification strategy

### 5.1 Evidence requirement (mới, ra đời từ lesson của audit)

Mọi task complete claim PHẢI kèm:
- `gh api` / `gh pr view` / `gh run view` output (cho PR/issue/CI state)
- `git log --oneline` output với hash
- File path + line number
- Test output (command invoked + stdout)

Lý do: tránh lặp lại incident Antigravity walkthrough hoặc Claude Code session cf5ac4a3 hallucinate task status. Không trust "tôi đã làm rồi" — trust evidence.

### 5.2 Phase gate acceptance

Mỗi phase có acceptance criteria cụ thể (xem plan file). Phase kế chỉ start sau khi phase trước pass acceptance với evidence attached.

### 5.3 E2E gate trước release

Release stable version CHỈ sau Phase M E2E suite pass 100% với local unreleased build (không dùng released package).

---

## 6. Open design questions

Resolve trong execution, không blocker cho spec approval:

1. **Agent auto-open browser reliability**: Spec 2025-11-25 nói MCP client MUST auto-open browser khi nhận 401 với `WWW-Authenticate: Bearer resource_metadata=...`. Claude Code, Codex CLI, Copilot, Antigravity hiện tại implement đầy đủ chưa? Test empirical trong Phase G5.
2. **Shared ONNX across wet+mnemo+crg daemons**: Ba daemon riêng đều load model qwen3-embed độc lập (3 copies RAM). Tạo 1 embedding daemon riêng share 3 server khác? Defer — phase sau nếu cần, không blocker.
3. **Stdio proxy auto-ensure race**: 2 agent start song song → cả 2 spawn daemon → conflict. Resolve qua atomic file lock + retry pattern.
4. **PSR commit prefix config**: verify PSR trong 12 repo support custom commit template qua `python-semantic-release` hoặc `semantic-release-monorepo`. Override ở Phase K4.
5. **Notion current Streamable HTTP compliance**: verify `better-notion-mcp` HTTP transport hiện dùng spec nào (2024-11-05 old, 2025-03-26, hoặc 2025-11-25). Đọc source trong Phase G6.
6. **Idle shutdown policy**: default local HTTP server idle bao lâu thì tự exit? Recommend: never shutdown by default, configurable qua env var `MCP_CORE_IDLE_TIMEOUT=<minutes>`.

---

## 7. Objectives mapping (O12-O19)

Nối tiếp O1-O11 của April 5 spec.

- **O12** — Unblock CI: tất cả 12 repo CI xanh 3 run liên tiếp trên ubuntu + windows + macos
- **O13** — GDrive single-folder invariant: wet + mnemo sync vào 1 appdata folder, token rotation không tạo duplicate
- **O14** — Streamable HTTP 2025-11-25 compliance: mcp-core + 6 credential server dùng unified `/mcp` endpoint
- **O15** — Unified OAuth 2.1 AS: self-hosted AS cho 5 server, delegated cho notion remote, UX relay form giữ nguyên
- **O16** — Resource consolidation: wet + mnemo + crg chạy long-running HTTP, share heavy state across Claude Code sessions
- **O17** — Multi-OS + multi-agent support: 12 repo CI matrix pass, `install_agent` ghi config đúng cho 7 agent
- **O18** — Docs/rules compliance: README accurate, profile accurate, pre-commit hook enforce `fix:`/`feat:` only từ 2026-04-10
- **O19** — Full/real/live E2E test pre-release: clean state, real credentials, build local, mọi action/mode của mọi server, concurrent session test

---

## 8. References

- MCP Streamable HTTP 2025-11-25 spec: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP Authorization spec: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- OAuth 2.1 draft: RFC 9470
- Google Drive API appdata scope: https://developers.google.com/drive/api/guides/appdata
- FastMCP Streamable HTTP deployment: https://gofastmcp.com/deployment/http
- Prior spec: `specs/2026-04-05-relay-redesign-and-production-hardening-design.md`
- Prior plan: `plans/2026-04-08-production-hardening-phase2.md`
