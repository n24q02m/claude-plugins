# MCP Core — Unified Transport & Authorization Design

**Date**: 2026-04-10
**Status**: Draft v2 (gap fixes applied, awaiting user review)
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
| Rename impact `mcp-relay-core` → `mcp-core` | **481 refs across 6 repos** (godot 0 refs) | — |
| wet-mcp embedding backend | **ONNX runtime primary + llama-cpp-python GGUF optional** | — |
| mnemo/crg graph backend | **SQLite + sqlite-vec + SQL graph tables** (NOT FalkorDB) | — |
| Claude Code HTTP transport support | **Verified via ~/.claude backups + microsoft_skills configs: `"type": "http"`** | — |
| Secrets exposure in `~/.claude/settings.local.json` + `.claude.json` backup | **7 real credentials hardcoded (GitHub PAT, Gemini, Cohere, Google Stitch API, email app passwords for 4 accounts, Telegram API creds)** | — |

### 1.2 User requirements (locked trong session 2026-04-10)

Từ các turn trao đổi của user:

1. **Best practice, best consolidate** ở mọi quyết định
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

**"Best consolidate" criteria** (định nghĩa cụ thể để đánh giá mọi decision):
- **Single source of truth** — 1 codebase cho cả local + remote mode, 1 auth path cho cả 2 flavor (self-hosted + delegated), 1 transport implementation cho cả 7 server
- **Zero duplicate infrastructure** — không có separate HTTP + SSE, không có separate stdio + HTTP handlers, không có per-server auth reimplementation
- **Minimum surface area** — mỗi server chỉ 1 entry point binary, mỗi operation chỉ 1 code path, mỗi credential store chỉ 1 encryption scheme
- **Maximum reuse** — chung crypto/transport/auth/lifecycle/install modules qua `mcp-core` library
- **Rollback safety** — rename + migration có thể revert qua git mà không lose credential state

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

**Timing**: Drop **ngay** trong major version bump (không grace period). Lý do: ecosystem chưa có external user ngoài 1 PR contributor, deprecation warning period chỉ thêm noise và tech debt.

**Rationale**:
- Spec 2025-11-25 định nghĩa Streamable HTTP là canonical transport
- 1 endpoint `/mcp` duy nhất (POST + GET + DELETE) thay vì HTTP + separate `/sse`
- stdio phức tạp (EOF, subprocess lifecycle, separate relay trigger)
- Multi-session trên 1 process (key lợi ích cho heavy servers)
- Session isolation qua `Mcp-Session-Id` header native từ spec

**Exception**: `better-godot-mcp` giữ stdio — không có credentials, process nhẹ, spawn per-session OK, 0 refs tới `mcp-relay-core` (verified qua grep).

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

**"Heavy state" definition**: resource shared-across-sessions (ONNX model weights, sqlite-vec index, rerank model, DocsDB) — loading once per server process saves 500MB-2GB RAM per additional session. Per-session state (client objects, IMAP pools, Telethon sessions) không phải heavy state — user-bound, không share được.

| Server | Transport | Local auth | Remote auth | Heavy state (shared across sessions) | Remote prereq |
|--------|-----------|-----------|-------------|--------------------------------------|---------------|
| **wet-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | ONNX embedding + reranker + DocsDB SQLite 1.5GB + SearXNG subprocess (+optional llama.cpp GGUF) | Doppler/Infisical master secret, Caddy + CF Tunnel |
| **mnemo-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | ONNX embedding + reranker + memories.db SQLite (sqlite-vec + SQL graph tables) | Doppler/Infisical master secret, Caddy + CF Tunnel |
| **better-code-review-graph** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | ONNX embedding + reranker + graph.db SQLite (sqlite-vec) | Doppler/Infisical master secret, Caddy + CF Tunnel |
| **better-telegram-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | Per-session Telethon (NOT shared heavy state) | Doppler/Infisical master secret, Caddy + CF Tunnel |
| **better-email-mcp** | HTTP only | Self-hosted AS | Self-hosted AS multi-user | Per-session IMAP pool (NOT shared heavy state) | Doppler/Infisical master secret, Caddy + CF Tunnel |
| **better-notion-mcp** | HTTP only | **Self-hosted AS** (paste Notion integration token) | **Delegated → Notion OAuth** | Per-session Notion client (NOT shared heavy state) | **Notion OAuth app registration (https://www.notion.so/my-integrations) + client_id/client_secret + redirect_uri** whitelist |
| **better-godot-mcp** | stdio only | — | — | Stateless CLI wrapper | n/a |

**Notion exception explanation**: Notion có real OAuth provider cho multi-user (`api.notion.com/v1/oauth`). Remote mode bắt buộc delegate để mỗi user authorize với chính Notion account của họ. Local mode vẫn dùng self-hosted AS với relay form paste integration token (đơn giản, không cần OAuth dance cho 1 user). Remote deployment là **blocker** nếu Notion OAuth app chưa register — không thể soft-fail.

### 2.5 Decision: mcp-core package (renamed from mcp-relay-core)

**Rename `mcp-relay-core` → `mcp-core`. Mở rộng scope. Base framework: FastMCP Python cho 3 heavy server (wet/mnemo/crg), `@modelcontextprotocol/sdk` TypeScript cho email/notion, stdio native cho godot.**

**Rename impact** (verified qua grep):

| Repo | Refs tới `mcp-relay-core` / `mcp_relay_core` | Action |
|------|----------------------------------------------|--------|
| `mcp-relay-core` (self) | — | Rename package directory + pyproject + GitHub repo |
| `wet-mcp` | ~180 refs | Update imports + pyproject dep + editable path |
| `mnemo-mcp` | ~120 refs | Update imports + pyproject dep + editable path |
| `better-code-review-graph` | ~90 refs | Update imports + pyproject dep + editable path |
| `better-telegram-mcp` | ~50 refs | Update imports + package.json dep |
| `better-email-mcp` | ~25 refs | Update imports + package.json dep |
| `better-notion-mcp` | ~16 refs | Update imports + package.json dep |
| `better-godot-mcp` | **0 refs** | No change |
| **Total** | **481 refs** | Automated sed + verification grep |

**Editable path update**: `pyproject.toml` line 120 trong wet-mcp hiện tại:
```toml
mcp-relay-core = { path = "../mcp-relay-core/packages/core-py", editable = true }
```
Sau rename:
```toml
mcp-core = { path = "../mcp-core/packages/core-py", editable = true }
```
Giả định user clone `mcp-core` cùng parent directory với các server repo. Document trong AGENTS.md.

**Layout mới**:

```
mcp-core/
├── packages/core-py/src/mcp_core/
│   ├── transport/
│   │   ├── streamable_http.py    # 2025-11-25 spec base (FastMCP backed)
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
│   │   ├── lock.py               # PID + port file lock (fcntl Unix / msvcrt Windows)
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

**Base framework decision rationale**:
- **FastMCP Python** đã implement Streamable HTTP 2025-11-25, có built-in session manager, OAuth middleware hook — tiết kiệm weeks viết transport layer
- **@modelcontextprotocol/sdk TS** cho email/notion có matching feature set
- godot giữ stdio native vì không cần shared state, 0 credentials, keep it simple

**Module mapping**: tất cả module của `mcp_relay_core` chuyển thành submodule của `mcp_core.crypto` + `mcp_core.auth.oauth.local_ui`. Không có logic nào bị lost, chỉ reorganize.

### 2.6 Decision: GDrive fix — drive.appdata scope

**wet-mcp + mnemo-mcp chuyển scope từ `drive.file` sang `drive.appdata`.**

**Root cause**: `drive.file` scope chỉ cho phép app xem file **do app tạo**. OAuth token rotation (refresh flow, re-consent, credential reset) invalidates prior token's ownership claim — new token không "thấy" folder cũ → `_find_or_create_folder()` tạo folder mới → duplicate. Verified trong `wet-mcp/src/wet_mcp/sync.py:43`.

**Rationale**:
- `drive.appdata` là scope Google thiết kế riêng cho "app config/data that user doesn't interact with directly"
- Zero duplicate by architectural design (1 appdata folder per user per OAuth client_id, persistent across tokens)
- Minimum scope (hẹp nhất trong Drive scopes)
- Không cần `permissions.create` workaround
- Không cần manual folder ID
- Data vẫn private của user (trong their drive nhưng không hiện Drive UI)

**Trade-off**: User không browse `docs.db` / `memories.db` trực tiếp. Không phải vấn đề vì không ai mở 1.5GB SQLite file thủ công.

**Migration**: one-time routine first run after upgrade — detect files trong old folders, upload to appdata, flag migrated. User re-consent OAuth 1 lần.

**Cleanup** (thực hiện qua rclone trong Phase G trước khi code fix):
- Xóa `wet-mcp/` + `wet-mcp (2)/` + stale `docs.db` trên GDrive
- Xóa `mnemo-mcp/` + `mnemo-mcp (1)/` + stale `memories.db` trên GDrive
- Recovery: nếu duplicate chứa data unique (ví dụ: db newer hơn), download trước khi xóa, merge thủ công sau upload appdata

### 2.7 Decision: CLI removal

**KHÔNG có CLI subcommand. Chỉ 1 entry point per server.**

**Mode detection trong entry point binary**:
- Nếu env `MCP_CORE_MODE=server` HOẶC được spawn bởi stdio proxy launcher HOẶC file lock indicates server role → chạy HTTP server
- Nếu stdin là pipe từ agent stdio client (default) → chạy stdio proxy + auto-ensure HTTP server qua lifecycle lock
- Race condition: 2 agents start cùng lúc → file lock với atomic create + retry (fcntl.flock Unix / msvcrt.locking Windows)

**Management qua MCP tool action** (mở rộng mega-tool hiện có). Mọi credential server expose matrix actions sau:

| Action | wet | mnemo | crg | telegram | email | notion |
|--------|:---:|:-----:|:---:|:--------:|:-----:|:------:|
| `status` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `install_agent` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `uninstall_agent` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `reset_credentials` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `shutdown_daemon` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `trigger_relay` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (local only) |

Semantic:
- `status` — server health, port, connected sessions, memory usage, uptime
- `install_agent(targets=[...])` — auto detect và write config files
- `uninstall_agent(targets=[...])` — cleanup
- `reset_credentials()` — trigger relay form re-submission, clear config.enc
- `shutdown_daemon()` — clean exit HTTP server (user có thể gọi trước khi upgrade)
- `trigger_relay()` — returns relay URL + force open in browser

Mỗi server expose thêm domain-specific actions (wet: search/extract/media, mnemo: memory, telegram: message/chat/media, etc.) — không thay đổi.

### 2.8 Decision: Agent config auto-write

**`mcp_core.install.agents` module support**. Priority order để test/document trước:

**Tier 1 (primary, must work ngay)**:

| Agent | Config file | Entry format |
|-------|-------------|-------------|
| Claude Code | `~/.claude/settings.json` hoặc `{project}/.mcp.json` | `{"type": "http", "url": "http://127.0.0.1:<port>/mcp", "headers": {"Authorization": "Bearer <token>"}}` |
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.<name>]` với `url`, `bearer_token_env_var` |
| GitHub Copilot (VSCode Insiders) | `{project}/.vscode/mcp.json` hoặc `~/AppData/Roaming/Code - Insiders/User/mcp.json` | `{"servers": {"<name>": {"type": "http", "url": "..."}}}` |

**Tier 2 (secondary, best-effort)**:

| Agent | Config file | Entry format |
|-------|-------------|-------------|
| Antigravity (Gemini CLI) | `~/.gemini/antigravity/mcp_config.json` | tương tự Claude Code |
| Cursor | `~/.cursor/mcp.json` | tương tự Claude Code |
| Windsurf | `~/.codeium/windsurf/mcp.json` | tương tự |
| OpenCode | `~/.config/opencode/opencode.json` (MCP section) | tương tự |

Tier 1 phải test empirical trong Phase M, Tier 2 có thể defer nếu time boxed. Merge logic: preserve existing entries, add/update entry cho server hiện tại, write back với backup (`.bak` kế bên original).

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
- Master secret trong Doppler (VM config) + Infisical (app secrets), rotation procedure documented per server repo AGENTS.md
- Rate limiting per user (token bucket) qua middleware
- Audit log: mọi authorize/token/revoke event
- Multi-user isolation test: user A không decrypt được user B credentials

**Infisical structure** (concrete, không placeholder):

```
project:   mcp-core-prod
environment: production
folders:
  /mcp-core/
    MASTER_SECRET          # base64 32 bytes, feeds PBKDF2
    JWT_PRIVATE_KEY_PEM    # RS256 signing key (rotatable)
    JWT_PUBLIC_KEY_PEM     # paired public key
  /wet-mcp/
    GDRIVE_OAUTH_CLIENT_ID
    GDRIVE_OAUTH_CLIENT_SECRET
    SEARXNG_CONFIG         # optional custom SearXNG endpoint
  /mnemo-mcp/
    GDRIVE_OAUTH_CLIENT_ID
    GDRIVE_OAUTH_CLIENT_SECRET
  /better-code-review-graph/
    GITHUB_APP_PRIVATE_KEY
    GITHUB_APP_CLIENT_ID
  /better-telegram-mcp/
    TELEGRAM_API_ID
    TELEGRAM_API_HASH
  /better-email-mcp/
    (no app-level secret — per-user IMAP creds only)
  /better-notion-mcp/
    NOTION_OAUTH_CLIENT_ID
    NOTION_OAUTH_CLIENT_SECRET
    NOTION_OAUTH_REDIRECT_URI
```

Universal-auth machine identity (Client ID `92ae6217-...` per memory) fetches at server start via `infisical export --format=dotenv --token=$INFISICAL_TOKEN`. Secrets never touched by user during runtime.

### 3.3 Credential flow (không đổi)

- Credentials KHÔNG bao giờ pass qua LLM chat context
- Relay form POST body nhận credentials, server process immediately, store encrypted
- No `set_env` MCP action anywhere
- Token exchange theo OAuth 2.1 standard

### 3.4 Pre-existing secret exposure (new section, incident documented)

**Finding**: `~/.claude/settings.local.json` và backups `~/.claude/backups/.claude.json.*` chứa hardcoded credentials đã commit vào disk trong prior sessions:
- `GITHUB_TOKEN` (personal access token)
- `GEMINI_API_KEY`
- `COHERE_API_KEY`
- `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` + `TELEGRAM_PHONE`
- `EMAIL_CREDENTIALS` cho 4 accounts (IMAP app passwords)
- Google Stitch API key (`X-Goog-Api-Key` header trong `.claude.json.backup` stitch entry)

**Impact**: Các credential này có thể có trong:
- Claude Code session history files (jsonl transcripts)
- Backup files theo timestamp
- Memory file-history versioning directory

**Fix ownership**: Không phải phạm vi spec này (không thuộc 12 repo). Nhưng cần:
1. User rotate tất cả secret trên
2. `~/.claude/settings.local.json` phải migrate sang Doppler/Infisical fetch-at-runtime pattern
3. Backup files sanitize (grep replace placeholders) trước khi sync bất cứ đâu
4. Spec này không làm thay — flag để user handle separately

**Enforce going forward**: MCP core credential load luôn qua Infisical, không qua env vars trực tiếp user set.

---

## 4. Backward compatibility & migration

### 4.1 Breaking changes

- **mcp-relay-core → mcp-core**: import path change, major version bump (v2.0.0). **Editable path** trong pyproject.toml của 3 downstream Python repo phải update (wet-mcp line 120, mnemo-mcp, crg).
- **stdio mode drop** cho 6 credential servers: major version bump per server
- **Old HTTP relay endpoints** (`/sse`, `/events/*`): bỏ hoàn toàn, không grace period (chưa có external user ngoài 1 PR contributor)
- **GDrive scope** `drive.file` → `drive.appdata`: user phải re-consent OAuth 1 lần

### 4.2 Migration path cho user

- Release current N.x.y: unchanged, no action needed
- Release N+1.0.0: stdio mode removed hoàn toàn, chỉ HTTP mode, rename mcp-relay-core → mcp-core
- Runtime một lần: data migration routine chạy first start sau upgrade (GDrive appdata, optional backup old config.enc)

Vì ecosystem này chưa có external user, skip grace period — release N+1.0.0 thẳng với mọi breaking change aggregated.

### 4.3 User migration tool

- `wet(action="install_agent", targets=["all"])` detect existing stdio entries trong agent config files, replace với HTTP entries
- Existing `config.enc` format compatible — AES-GCM machine key scheme không đổi
- GDrive migration: `wet(action="reset_credentials")` triggers re-consent với new scope, routine chạy appdata migration once.

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

## 6. Risk analysis & rollback

### 6.1 Per-server rollback

| Risk | Likelihood | Impact | Mitigation | Rollback |
|------|:---:|:---:|------------|----------|
| Rename `mcp-relay-core` → `mcp-core` breaks editable path in downstream | High | Medium | Update all 3 downstream `pyproject.toml` in **same commit** as rename; verify `uv sync` + test run before push | `git revert` rename commit → downstream imports still work via legacy package name |
| FastMCP base framework incompatible với existing mcp-relay-core APIs | Medium | High | Spike FastMCP integration in Phase H1 (1 server only: wet-mcp) before rolling to mnemo + crg | Keep legacy Starlette custom transport code path in `mcp_core.transport.legacy.py`, flip flag per server |
| GDrive appdata migration corrupts existing databases | Low | High | Upload to appdata **first**, verify checksum, only then delete old folders; keep rclone backup local before destructive delete | rclone restore từ local backup trong 24h |
| OAuth 2.1 auto-browser UX broken in some agent (e.g. Antigravity can't open browser) | High | Medium | Phase G5 empirical test before rolling AS; fallback: print URL to stderr for manual copy | Per-agent compat matrix; revert to legacy relay trigger for agents that fail |
| Pre-commit prefix hook blocks urgent fix PR | Medium | Low | Hook only on push, not on amend; bypass documented but discouraged | Remove hook commit, push fix, re-add hook |
| Multi-user remote isolation bug leaks User A's creds to User B | Low | Critical | Phase L3 fuzz test với 10 concurrent users, cross-decrypt attempt fails | Kill remote mode immediately, force all users back to local, rotate master secret |
| Notion OAuth app registration delays remote launch | High | Low | Register Notion OAuth app before Phase K; local mode unaffected | Remote notion stays opt-out until registered; other 5 remote servers unaffected |

### 6.2 PR review SLA

**Pending 246 PRs** — aggressive processing strategy:
- Bot PRs (Renovate, Dependabot): batch review + merge trong Phase G1-G4 nếu CI xanh và không touch auth/transport code
- Human PRs (1 only: OdinYkt telegram #277): review individually với context về Phase 3 rewrite; có thể close với explanation nếu conflict với new architecture, OR cherry-pick useful changes
- SLA: Phase G kết thúc ≤ 50 open PRs (review ≥ 200)

### 6.3 Test credential strategy

E2E tests cần real credentials cho mọi server. Strategy:
- **Dedicated test accounts**: test Telegram account, test Notion workspace, test email (Gmail app password), test GitHub App
- Stored trong Infisical `mcp-core-test` project (separate environment)
- Rotated monthly
- CI fetches qua machine identity, không commit trong GitHub secrets
- Local dev dùng same Infisical project

### 6.4 Circular dependency risk

`mcp-core` depends on `web-core` cho HTTP client utilities. `web-core` potentially imports `mcp-core` nếu cần MCP client. **Resolution**: `web-core` KHÔNG import `mcp-core`. `mcp-core` có internal `http_client.py` duplicate nếu cần thiết. Verify qua dependency graph check trong Phase H.

---

## 7. Open design questions

Resolve trong execution, không blocker cho spec approval:

1. **Agent auto-open browser reliability**: Spec 2025-11-25 nói MCP client MUST auto-open browser khi nhận 401 với `WWW-Authenticate: Bearer resource_metadata=...`. Claude Code, Codex CLI, Copilot, Antigravity hiện tại implement đầy đủ chưa? Test empirical trong Phase G5.
2. **Shared ONNX across wet+mnemo+crg daemons**: Ba daemon riêng đều load model qwen3-embed độc lập (3 copies RAM). Tạo 1 embedding daemon riêng share 3 server khác? Defer — phase sau nếu cần, không blocker.
3. **Stdio proxy auto-ensure race**: 2 agent start song song → cả 2 spawn daemon → conflict. Resolve qua atomic file lock + retry pattern (fcntl Unix / msvcrt Windows).
4. **PSR commit prefix config**: verify PSR trong 12 repo support custom commit template qua `python-semantic-release` hoặc `semantic-release-monorepo`. Override ở Phase K4.
5. **Notion current Streamable HTTP compliance**: verify `better-notion-mcp` HTTP transport hiện dùng spec nào (2024-11-05 old, 2025-03-26, hoặc 2025-11-25). Đọc source trong Phase G6.
6. **Idle shutdown policy**: default local HTTP server idle bao lâu thì tự exit? Recommend: never shutdown by default, configurable qua env var `MCP_CORE_IDLE_TIMEOUT=<minutes>`.

---

## 8. Objectives mapping (O12-O19)

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

## 9. References

- MCP Streamable HTTP 2025-11-25 spec: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP Authorization spec: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- OAuth 2.1 draft: RFC 9470
- Google Drive API appdata scope: https://developers.google.com/drive/api/guides/appdata
- FastMCP Streamable HTTP deployment: https://gofastmcp.com/deployment/http
- Prior spec: `specs/2026-04-05-relay-redesign-and-production-hardening-design.md`
- Prior plan: `plans/2026-04-08-production-hardening-phase2.md`
