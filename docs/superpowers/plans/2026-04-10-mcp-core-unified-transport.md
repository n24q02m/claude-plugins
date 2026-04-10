# MCP Core — Unified Transport & Authorization Plan

**Spec**: `specs/2026-04-10-mcp-core-unified-transport-design.md`
**Date**: 2026-04-10
**Status**: Draft for review
**Predecessor**: `plans/2026-04-08-production-hardening-phase2.md` (Phase A/D/F DONE, Phase B/C/E revised hoặc subsumed by this plan)

---

## Execution graph

```
  Phase G (unblock P0) ─┬──> Phase I (mcp-core) ──> Phase J (server migration) ──> Phase K (docs)
                        │                                                            │
  Phase H (GDrive P0) ──┘                                                             │
                                                                                       ├──> Phase M (E2E + release)
  Phase L (PR cleanup) ────────────────────────────────────────────────────────────────┘
```

- Phase G + H: parallel, P0 blockers
- Phase I: needs G pass (CI green, localhost HTTP verified)
- Phase J: needs I pass (mcp-core v2.0.0 published)
- Phase K: needs J mostly done (docs describe new architecture)
- Phase L: parallel với I/J/K (PR review independent of refactor)
- Phase M: final gate, needs all previous

**Critical path**: G → I → J → M (ước lượng dài nhất)

---

## Legend

- `[ ]` task pending
- `[>]` in progress
- `[x]` completed
- `[!]` blocked
- Size: `[S]` < 2h, `[M]` 2-8h, `[L]` 8-24h, `[XL]` > 24h

Mỗi task phải complete với **evidence** (gh API output, git hash, file:line, test output) — không trust claim without evidence.

---

## Phase G — Unblock P0 blockers

**Goal**: Clear blockers để Phase I/J có thể khởi động an toàn.

### G1: [M] Resolve better-telegram-mcp merge conflict

- Repo: `better-telegram-mcp`
- Files: `src/better_telegram_mcp/transports/http_multi_user.py` (DU state) + 11 related dirty files
- Steps:
  - `git status --short` để liệt kê
  - `git diff HEAD` và `git diff MERGE_HEAD` cho mỗi file
  - Merge manually, preserve Phase B2 OAuth work nếu còn relevant với design mới
  - Run `uv run pytest` để verify
  - Commit với `fix: resolve merge conflict in http_multi_user.py post Phase B2`
- Acceptance:
  - `git status` clean
  - Pytest pass
  - Evidence: git log hash, pytest summary

### G2: [L] Diagnose + fix wet-mcp CI red

- Repo: `wet-mcp`
- Current state: 0/10 pass last 10 CI runs
- Steps:
  - `gh run list -R n24q02m/wet-mcp --limit 10 --json databaseId,conclusion,displayTitle`
  - `gh run view <id> -R n24q02m/wet-mcp --log-failed` để identify root cause (lint, test, build, etc.)
  - Fix hoặc revert offending commits
  - Push fix, monitor 3 consecutive CI runs green
- Acceptance:
  - 3 consecutive CI runs green trên ubuntu + windows + macos
  - Evidence: gh run list output với status success

### G3: [M] Dismiss 15 CodeQL false positives

- Repos: wet-mcp (10), mnemo-mcp (3), web-core (2)
- All alerts: `py/incomplete-url-substring-sanitization` trong test files
- Steps per repo:
  - `gh api "repos/n24q02m/<repo>/code-scanning/alerts?state=open"` để list
  - Per alert: `gh api -X PATCH "repos/n24q02m/<repo>/code-scanning/alerts/<num>" -f state=dismissed -f dismissed_reason="false positive" -f dismissed_comment="Test code, not production path. URL substring check là acceptable for test URLs."`
- Acceptance:
  - `gh api ".../code-scanning/alerts?state=open"` returns empty array cho cả 3 repo
  - Evidence: per-repo dismissed alert count

### G4: [M] Fix 2 Dependabot alerts trong wet-mcp

- Alerts:
  - `langchain-core` incomplete f-string validation (medium)
  - `cryptography` buffer overflow (medium)
- Steps:
  - Identify patched versions từ alert body
  - Update `pyproject.toml` dependencies
  - `uv lock --upgrade-package langchain-core --upgrade-package cryptography`
  - Run test suite
  - Commit `fix(deps): bump langchain-core and cryptography for security patches`
- Acceptance:
  - `gh api ".../dependabot/alerts?state=open"` returns empty
  - Pytest pass
  - Evidence: commit hash, test output

### G5: [L] Verify Claude Code localhost HTTP reliability (CRITICAL BLOCKER)

- **Blocker critical cho Phase I/J design**. Nếu fail → abort Option B, redesign.
- Steps:
  - Build minimal FastMCP HTTP server cho test (không commit, throwaway code trong `/tmp/`)
  - Start server bind `127.0.0.1:41700` expose `/mcp` endpoint với 1 simple tool `ping`
  - Create test `.mcp.json` ở `~/.claude/settings.json` hoặc `{project}/.mcp.json`:
    ```json
    {"mcpServers": {"localtest": {"type": "http", "url": "http://127.0.0.1:41700/mcp"}}}
    ```
  - Restart Claude Code hoặc `/reload-plugins`
  - Verify Claude Code connects — check `/mcp` command, list tools
  - Invoke `localtest.ping` tool
  - Test 401 flow: server returns 401, Claude Code auto-opens browser?
- Acceptance:
  - Round-trip tool call thành công
  - 401 auto-open browser verified (or documented behavior nếu not supported)
  - Evidence: Claude Code console screenshot + server log

**Fallback nếu G5 fail**: Option B không khả thi. Revise spec để giữ stdio mode default, HTTP chỉ cho remote. Re-estimate Phase I/J.

### G6: [S] Verify notion-mcp current transport spec version

- Repo: `better-notion-mcp`
- Steps:
  - Read `src/**/*.ts` tìm HTTP transport implementation
  - Check endpoint path (`/mcp` vs `/sse` separate)
  - Check session header (`Mcp-Session-Id` vs custom)
  - Check `MCP-Protocol-Version` header handling
  - Determine spec version: 2024-11-05 | 2025-03-26 | 2025-11-25
- Acceptance:
  - Document finding trong `notion-current-transport.md` note file
  - Evidence: file:line citations

### Phase G acceptance criteria

- [ ] G1-G6 all complete với evidence
- [ ] All 11 code repos CI green ≥3 consecutive runs trên 3 OSes
- [ ] Claude Code localhost HTTP empirical work confirmed (G5)
- [ ] 0 open CodeQL alerts, 0 open Dependabot alerts
- [ ] Spec design decisions không bị G5 invalidate

---

## Phase H — GDrive single folder invariant

**Goal**: wet-mcp + mnemo-mcp sync vào 1 appdata folder duy nhất, token rotation không tạo duplicate. Cleanup 4.5 GB stale data.

### H1: [M] Implement scope upgrade + migration routine trong wet-mcp

- Repo: `wet-mcp`
- File: `src/wet_mcp/sync.py`
- Changes:
  - Line 43: `_SCOPE = "https://www.googleapis.com/auth/drive.appdata"`
  - Add `_migrate_from_drive_file_to_appdata(token) -> bool`: detect existing files trong `wet-mcp/` folder qua old-scope fallback (temporary broader scope for migration only), upload to appdata space, flag migrated
  - Modify `_find_or_create_folder` → `_get_appdata_folder_id` (appdata là well-known ID `appDataFolder`)
  - Modify `_upload_file` để target parent = `appDataFolder`
- Tests: mock Drive API, verify migration happy path + idempotency (retry safe)
- Acceptance:
  - `pytest tests/test_sync.py` pass
  - Manual dry-run trên dev account OK
  - Evidence: test output, file diff

### H2: [M] Same pattern cho mnemo-mcp

- Repo: `mnemo-mcp`
- File: `src/mnemo_mcp/sync.py`
- Identical changes
- Tests: tương tự H1
- Acceptance: tương tự H1

### H3: [M] Token rotation regression test

- Scenario: mock 2 different OAuth tokens representing same user re-authenticate
- Verify: 2nd token thấy cùng `appDataFolder`, không tạo folder mới
- Files: `tests/test_sync_token_rotation.py` cho cả 2 repos
- Acceptance: test pass, scenario tài liệu hoá

### H4: [S] User re-consent flow

- Relay form detect scope mismatch qua OAuth scope claim
- Display warning: "Scope changed to drive.appdata, need re-authorize"
- Link tới re-authorization flow
- Acceptance: post-reconsent, sync works OK với appdata

### H5: [S] Cleanup old duplicate folders qua rclone

- **DESTRUCTIVE**. Precondition: H1-H4 pass, data đã migrate verified OK.
- Confirm với user 1 lần nữa trước khi chạy.
- Commands (in order):
  ```
  rclone lsd "echovault-gdrive:" | grep -E "wet-mcp|mnemo-mcp"   # verify state
  rclone delete "echovault-gdrive:wet-mcp (2)/docs.db"
  rclone rmdir  "echovault-gdrive:wet-mcp (2)/"
  rclone delete "echovault-gdrive:wet-mcp/docs (1).db"
  rclone delete "echovault-gdrive:mnemo-mcp (1)/memories.db"
  rclone rmdir  "echovault-gdrive:mnemo-mcp (1)/"
  rclone lsd "echovault-gdrive:" | grep -E "wet-mcp|mnemo-mcp"   # verify cleanup
  ```
- Acceptance:
  - `rclone lsd` không còn `wet-mcp (2)/`, `mnemo-mcp (1)/`
  - Stale `docs (1).db` gone
  - `wet-mcp/docs.db` (bản stale Mar 12) có thể giữ như archive hoặc xóa nếu user confirm
  - Storage freed ~4.5 GB
  - Evidence: rclone lsd output before + after

### Phase H acceptance criteria

- [ ] H1-H5 complete với evidence
- [ ] Token rotation test pass
- [ ] Manual test: clean state → relay → sync → no new folder created
- [ ] ~4.5 GB freed trong gdrive

---

## Phase I — mcp-core rename + core modules

**Goal**: `mcp-core` v2.0.0 published, ready cho dependent servers migrate.

### I0: [M] Repo rename mcp-relay-core → mcp-core

- Steps:
  - `gh api -X PATCH repos/n24q02m/mcp-relay-core -f name=mcp-core`
  - Update local remote: `git remote set-url origin git@github.com:n24q02m/mcp-core.git`
  - Update package names:
    - Python: `pyproject.toml` `name = "mcp-core"` (was `mcp-relay-core`)
    - TS: `package.json` `"name": "@n24q02m/mcp-core"` (was `@n24q02m/mcp-relay-core`)
  - Directory rename: `packages/core-py/src/mcp_relay_core/` → `packages/core-py/src/mcp_core/`
  - Update all internal imports: `from mcp_relay_core` → `from mcp_core`
  - Update README.md title + install instructions
  - Update CLAUDE.md references
  - Update `.claude-plugin/plugin.json` hoặc marketplace.json nếu có entries
  - PSR config update: repo name, package name
- Acceptance:
  - Repo accessible tại `github.com/n24q02m/mcp-core`
  - Package publishable với tên mới
  - Internal tests pass post-rename
  - Evidence: gh repo view + git log + pytest output

### I1: [XL] Implement `mcp_core.transport.streamable_http`

- File: `packages/core-py/src/mcp_core/transport/streamable_http.py`
- Python implementation:
  - Option A: wrap FastMCP's Streamable HTTP (if stable)
  - Option B: implement directly per spec 2025-11-25
  - Recommend A nếu FastMCP current spec compliant, B nếu không
- Endpoints:
  - `POST /mcp`: parse JSON-RPC body, branch on `Accept` header (`application/json` vs `text/event-stream`), return JSON response OR open SSE stream
  - `GET /mcp`: server-initiated stream với `Last-Event-ID` resumption support
  - `DELETE /mcp`: session termination
  - `GET /.well-known/oauth-protected-resource`: spec metadata endpoint cho 401 flow
- Components:
  - Session manager: crypto-strong UUID, in-memory map keyed by `Mcp-Session-Id`
  - Event store interface: `InMemoryEventStore` default, pluggable `RedisEventStore` future
  - Origin validation middleware
  - `MCP-Protocol-Version` header handling (default `2025-03-26` if missing per spec)
- TypeScript equivalent: `packages/core-ts/src/mcp_core/transport/streamable-http.ts`
- Tests:
  - POST JSON response
  - POST SSE upgrade
  - GET server stream với Last-Event-ID replay
  - DELETE session termination
  - 404 on expired session
  - Origin rejection
- Acceptance: spec compliance test suite 100% pass

### I2: [XL] Implement `mcp_core.auth.oauth`

- Files:
  - `provider.py` — Self-hosted OAuth 2.1 AS
    - `/authorize` endpoint: render `local_ui.py` form hoặc `remote_ui.py` login tùy mode
    - `/token` endpoint: validate auth code + PKCE, issue JWT
    - `/register` (DCR RFC 7591)
    - `/revoke`
    - `/.well-known/oauth-authorization-server`
  - `delegated.py` — Delegated OAuth client wrapper (cho notion remote)
    - Config: upstream authorize URL, token URL, client ID, client secret (từ env/Infisical)
    - `/authorize` redirect tới upstream
    - Callback handler: exchange upstream code → upstream token → wrap trong own JWT cho client
  - `jwt_issuer.py` — RS256 JWT signing, key rotation
  - `local_ui.py` — Relay form HTML renderer (absorb `mcp_relay_core.browser` existing template)
  - `remote_ui.py` — Login/consent UI for remote mode
  - `user_store/single_user.py` — Local mode, config.enc backed, 1 user
  - `user_store/multi_user.py` — Remote mode, per-user encrypted store, PBKDF2 600k
  - `middleware.py` — Streamable HTTP auth middleware, validate bearer, inject user context
- TypeScript equivalent: `packages/core-ts/src/mcp_core/auth/oauth/*`
- Tests:
  - Full OAuth 2.1 authorization code + PKCE flow end-to-end
  - DCR flow
  - JWT signing + validation
  - Token expiry + refresh
  - Multi-user isolation (user A cannot decrypt user B creds)
  - Delegated flow mock với mock upstream
- Acceptance: RFC 6749 + 9470 compliance tests pass

### I3: [M] Refactor `mcp_core.crypto` + `mcp_core.lifecycle`

- Move existing modules:
  - `mcp_relay_core.config` → `mcp_core.crypto.config_enc`
  - `mcp_relay_core.session_lock` → `mcp_core.crypto.session_lock`
  - Cross-server key sharing logic → `mcp_core.crypto.key_sharing`
- New:
  - `lifecycle/lock.py`: atomic PID + port file lock, retry pattern cho race condition
  - `lifecycle/watchdog.py`: idle shutdown timer, health endpoint
- Port existing tests từ mcp-relay-core
- Acceptance: ported tests pass, new lock module tests pass

### I4: [M] Implement `mcp_core.transport.stdio_proxy`

- Thin binary: read stdin JSON-RPC frame → HTTP POST local server → write response frame to stdout
- Auto-ensure local HTTP server running (lifecycle lock + spawn if needed)
- Handle stdin EOF → graceful shutdown
- Handle HTTP error → forward as JSON-RPC error to stdout
- Tests: mock agent stdin + mock local server, verify forward + response
- Acceptance: round-trip test pass

### I5: [M] Implement `mcp_core.install.agents`

- Module: `mcp_core.install.agents`
- Functions:
  - `detect_agent_config_paths() -> dict[str, Path]` — OS-aware detection per agent
  - `read_config(agent: str, path: Path) -> dict` — parse JSON/TOML preserving structure
  - `write_config_entry(agent, path, name, url, token)` — merge entry
  - `remove_config_entry(agent, path, name)`
- Per-agent templates trong `templates/`
- Tests:
  - Mock existing config files per format
  - Verify merge preserves other entries
  - Verify idempotent write
  - Dry-run against real config files (read-only)
- Acceptance: mock tests pass, dry-run OK on local machine

### I6: [S] Publish mcp-core v2.0.0

- PSR trigger via commit conventional prefix
- Publish to npm: `@n24q02m/mcp-core@2.0.0`
- Publish to PyPI: `mcp-core==2.0.0`
- Verify: `uv pip install mcp-core`, `npx @n24q02m/mcp-core --version`
- Acceptance:
  - Both registries show v2.0.0
  - Install work trong clean venv
  - Evidence: PyPI + npm URLs

### Phase I acceptance criteria

- [ ] I0-I6 complete với evidence
- [ ] mcp-core v2.0.0 published PyPI + npm
- [ ] All unit tests pass (ported + new)
- [ ] Integration test: Streamable HTTP server + mock OAuth client end-to-end
- [ ] 7 dependent repos chưa update dep version (will happen in Phase J)

---

## Phase J — Migrate 6 credential servers to HTTP-only

**Goal**: wet/mnemo/crg/telegram/email/notion chạy HTTP-only mode với mcp-core v2.0.0.

### J1: [XL] wet-mcp migration

- Bump `mcp-core` dep → 2.0.0
- Update imports: `from mcp_relay_core` → `from mcp_core`
- Remove stdio server entry code (old `server.py` stdio path)
- New entry `src/wet_mcp/__main__.py`:
  - Mode detection (server vs stdio proxy)
  - Server mode: `from mcp_core.transport.streamable_http import create_app`, `from mcp_core.auth.oauth.middleware import add_oauth`, register wet tools, bind 127.0.0.1
  - Stdio proxy mode: `from mcp_core.transport.stdio_proxy import run_proxy; run_proxy(ensure_daemon=True)`
- Shared state: `src/wet_mcp/shared_state.py` — singletons cho ONNX, DocsDB, SearXNG, GDrive sync loop
- Per-session state: dict keyed by `Mcp-Session-Id`, cleanup on session end
- Relay form UI: extend `mcp_core.auth.oauth.local_ui` với wet-specific fields (Jina, Gemini, OpenAI, Cohere, GDrive consent)
- New MCP tool actions (extend `wet` mega-tool):
  - `wet(action="status")`
  - `wet(action="install_agent", targets=[...])`
  - `wet(action="uninstall_agent", targets=[...])`
  - `wet(action="reset_credentials")`
- Delete: `relay_setup.py` (replaced by mcp-core), old stdio code
- Update test suite cho HTTP mode
- Acceptance:
  - Server starts, binds port, exposes `/mcp`
  - Relay flow work (click form → submit → auth)
  - 3 concurrent sessions share 1 ONNX model load
  - `install_agent` writes correct `.mcp.json`
  - All tests pass
  - Evidence: process listing, port listening, tool invocation logs

### J2: [XL] mnemo-mcp migration

- Same pattern as J1
- Shared state: ONNX, memories.db
- Relay form fields: provider API keys, GDrive consent
- Acceptance: same criteria

### J3: [XL] better-code-review-graph migration

- Same pattern
- Shared state: ONNX, graph.db
- Relay form fields: provider API keys
- Acceptance: same

### J4: [XL] better-telegram-mcp migration

- Bump mcp-core dep
- Use `mcp_core.transport.streamable_http` as base
- Self-hosted AS với 2 modes:
  - Local: paste Bot Token hoặc phone/API_ID/API_HASH
  - Remote: per-user form, multi-user Telethon sessions
- Per-session Telethon connection (NOT shared across users)
- **Reshape PR #277 logic**:
  - Hub + per-user queue + backpressure: giữ
  - Remove `GET /events/telegram` separate endpoint
  - Push events qua `GET /mcp` server-initiated stream của cùng session (per 2025-11-25 spec)
  - Per-user isolation qua `Mcp-Session-Id` mapping to user_id
- Delete: `http_multi_user.py` old bespoke auth path (sau khi G1 resolve)
- Acceptance:
  - Local + remote modes work
  - SSE event push through `/mcp` GET stream verified
  - Per-user isolation test pass
  - Test với real Telegram account

### J5: [XL] better-email-mcp migration

- TypeScript, use `@n24q02m/mcp-core` TS package
- Same pattern, per-session IMAP pool
- Relay form: email + password / app password
- Optional: delegated OAuth to Gmail/Outlook (nice-to-have, defer nếu phức tạp)
- Acceptance: same criteria as J4

### J6: [L] better-notion-mcp migration

- TypeScript, use `@n24q02m/mcp-core` TS package
- **Exception server** — 2 auth variants:
  - Local: self-hosted AS, paste Notion integration token (form)
  - Remote: **delegated** to Notion OAuth (`api.notion.com/v1/oauth`)
- Per-session Notion client
- Acceptance:
  - Local mode: paste token form work
  - Remote mode: delegate flow work (mock if no real notion OAuth credentials)
  - Evidence: flow test output

### J7: [M] OdinYkt PR #277 handling

- Comment on PR explaining architecture change (Streamable HTTP spec 2025-11-25, SSE via `/mcp` GET stream)
- 2 options:
  - Offer to rebase on behalf of OdinYkt (requires their consent)
  - Request OdinYkt rebase theo hướng mới, provide spec reference
- Nếu OdinYkt không respond trong reasonable time → close PR với explanation, extract useful logic vào J4 implementation
- Acceptance: PR merged (preferred) hoặc closed with clear comment

### Phase J acceptance criteria

- [ ] J1-J7 complete với evidence
- [ ] 6 credential servers run HTTP mode, stdio mode removed
- [ ] `install_agent` tool writes config cho Claude Code + Codex + Copilot + Antigravity + Cursor + OpenCode
- [ ] Manual test: connect từ Claude Code local → relay flow → tool invoke cho mỗi server
- [ ] stdio proxy tested với 1 legacy stdio-only agent (e.g., test agent)
- [ ] Evidence: per-server test log, screenshots, process listings

---

## Phase K — Docs, rules, profile

**Goal**: Tất cả docs accurate, rules enforced, profile consistent.

### K1: [L] Per-repo README audit + fix

- 7 MCP server repos: tool count, feature list, install command, badges, CHANGELOG latest entry
- `mcp-core`: new README reflecting expanded scope (transport + auth + lifecycle + crypto + install)
- `qwen3-embed`, `web-core`: scope clarification (shared libraries, KHÔNG MCP servers)
- `claude-plugins`: marketplace entries sync với new versions
- `n24q02m` profile: sửa "8 MCP servers" → "7 MCP servers" nếu có stale reference
- Acceptance: per-repo checklist pass, evidence = diff URL

### K2: [S] n24q02m profile README update

- Add: Streamable HTTP mode section trong Design Philosophy
- Update: Libraries section (`mcp-core` thay `mcp-relay-core`)
- Verify: productions list accurate
- Acceptance: README reviewed + committed

### K3: [M] Commit prefix enforcement pre-commit hook

- Hook content: regex check `^(fix|feat)(\([a-z0-9-]+\))?:` OR reject
- Breaking change check: reject `!` indicator, suggest `BREAKING CHANGE:` footer
- Apply to 12 repos via `.pre-commit-config.yaml`
- Test: make 1 commit với `chore:` prefix → hook rejects
- Acceptance: hook catches violation, 12 repos enforced

### K4: [M] PSR + Renovate config prefix override

- PSR config per repo (`pyproject.toml` `[tool.semantic_release]` hoặc `release.config.js`):
  - Release commit template: `fix(release): vX.Y.Z` (was `chore(release):`)
  - Version bump rules: `fix:` = patch, `feat:` = minor, `BREAKING CHANGE:` footer = major
- Renovate `renovate.json` per repo:
  - `"commitMessagePrefix": "fix(deps):"` (was `chore(deps):`)
- Test: run PSR dry-run + Renovate preview, verify prefix
- Acceptance: 12 repos config updated, sample commit passes hook

### K5: [S] Historical bad prefix policy document

- Add memory entry: accept historical commits as-is, enforce from 2026-04-10 onwards
- Telegram `feat!:` historical: document in memory as "pre-enforcement"
- Acceptance: memory entry committed

### Phase K acceptance criteria

- [ ] K1-K5 complete
- [ ] Pre-commit hook catches violation in test commit
- [ ] Profile README accurate
- [ ] Evidence: README diffs, hook output, sample commit test

---

## Phase L — PR/issue/security cleanup

**Goal**: 246 open PRs + 16 issues processed.

### L1: [XL] Per-repo PR review batch

- Order: wet → mnemo → crg → telegram → email → notion → godot → mcp-core → claude-plugins → qwen3-embed → web-core
- Per repo:
  - List PRs: `gh pr list -R n24q02m/<repo> --state open --json number,title,author,labels,additions,deletions`
  - Categorize: security, fix, perf, test, renovate, cleanup
  - Review order: security first, then fix/perf, then test, then renovate
  - Per PR:
    - Read diff: `gh pr diff <num> -R ...`
    - Assessment: merge (valid + clean) / close (duplicate/garbage/inferior) / rebase (good idea needs update)
  - Present summary table to user:
    - Columns: PR#, author, category, assessment, reasoning
  - User bulk-approves routine decisions, inline-reviews top-5 concerning
  - Execute decisions: `gh pr merge` hoặc `gh pr close --comment "..."` per decision
- Acceptance:
  - Each of 246 PRs có decision + comment
  - Evidence: summary table per repo + action log

### L2: [M] OdinYkt PR #277 (coordinate với J7)

- See J7

### L3: [M] Resolve 16 open issues

- Per repo:
  - `gh issue list -R n24q02m/<repo> --state open --json number,title,labels`
  - Categorize: dependency-dashboard (keep, auto-managed), tracking-issue (keep, update status), external-request (respond + close), bug-report (fix or defer), feature-request (defer or close)
  - Execute
- Acceptance: each issue có decision + comment

### L4: [S] CodeQL — done trong G3

### L5: [S] Dependabot — done trong G4

### Phase L acceptance criteria

- [ ] 246 PRs processed với decision + comment
- [ ] 16 issues processed
- [ ] 0 open CodeQL/Dep alerts (sustained from G)
- [ ] Evidence: per-repo summary, action log

---

## Phase M — E2E full/real/live test + release

**Goal**: Full E2E test với local unreleased build, fix bugs, release stable.

### M1: [S] Clean state per server

- Delete `~/.config/<server>/config.enc` cho cả 6 credential servers
- Unset env vars
- Delete GDrive appdata (manual via rclone nếu cần)
- Delete lifecycle lock files
- Acceptance: mỗi server start trong `AWAITING_SETUP` state

### M2: [L] Build local unreleased

- Python repos (wet, mnemo, crg, telegram): `uv build && uv tool install dist/*.whl`
- TypeScript repos (email, notion, godot): `bun build && bun link`
- mcp-core: build + link as local dep
- Install order: mcp-core first, then dependents
- Acceptance: 6 servers installed from local builds, không dùng PyPI/npm released versions

### M3: [L] Relay flow test per server (1-1 với user)

- Start each server local
- `wet(action="install_agent", targets=["claude_code"])` để write Claude Code config
- Reload Claude Code plugins
- Invoke tool → server returns 401 → Claude Code auto-opens browser → relay form → user paste credentials → submit → tool retries → success
- Verify config.enc written, future calls work
- Acceptance: flow works per server (6 servers × 1 flow each)

### M4: [XL] Comprehensive tool coverage test

- Per server: call MỌI action của mega-tool
  - wet: search, extract, media, setup, config, help (mọi action/mode)
  - mnemo: memory all actions
  - crg: graph, query, review, config, setup, help
  - telegram: message, chat, media, contact
  - email: messages, folders, attachments, send
  - notion: databases, pages, blocks, comments, file_uploads, users, workspace
  - godot: 17 mega-tools
- Real credentials (từ Infisical hoặc user provide live)
- Không mock
- Acceptance: mỗi action return valid result (không exception, không timeout)

### M5: [M] Concurrent session test

- 3 Claude Code sessions song song, đều point tới cùng local HTTP server
- Each invoke different tools cùng lúc
- Verify: 1 daemon process, 3 sessions, no deadlock, ONNX loaded 1 lần (memory check)
- Evidence: `ps` output, memory usage, timing
- Acceptance: concurrent work OK, memory = 1x not 3x

### M6: [L] Remote mode test (self-host)

- Deploy 1 server (email hoặc notion) lên oci-vm-prod
  - `make up-oci-<server>-remote` với Infisical secrets
  - Caddy reverse proxy + CF Tunnel
- Test OAuth 2.1 flow:
  - DCR client registration
  - Authorize với simulated user A
  - Token exchange
  - Tool invoke với user A token
- Multi-user test: authorize user B, verify B không access user A data
- Acceptance: remote mode work, isolation verified

### M7: [L] Cross-OS test

- Verify CI matrix ubuntu + windows + macos xanh cho 11 code repos
- Manual smoke test:
  - Windows (primary dev machine): wet-mcp HTTP server start, relay flow, 1 tool call
  - WSL2 Ubuntu: tương tự
  - macOS: skip nếu không có máy, trust CI
- Acceptance: CI 3 runs per OS per repo pass, manual smoke pass

### M8: [?] Fix bugs found in M1-M7

- Document each bug với repro
- Fix + retest
- Size unknown, depends on discoveries
- Acceptance: all bugs fixed, retest pass

### M9: [M] Release stable

- Tag release per repo via PSR (commits qua Phase G-L đã trigger bump)
- CD publish: PyPI + npm
- Update marketplace: `claude-plugins/plugins/<name>/` sync
- Update n24q02m profile README với version list
- Acceptance:
  - Packages published với new versions
  - Installable via `uvx <server>` / `npx @n24q02m/<server>`
  - Marketplace updated
  - Evidence: PyPI/npm URLs, git tags, marketplace diff

### Phase M acceptance criteria

- [ ] M1-M9 complete
- [ ] 7 servers released với new versions
- [ ] Marketplace updated
- [ ] E2E test suite documented + committed cho regression
- [ ] Evidence: test logs, release URLs, screenshots

---

## Rollback strategy

### Nếu Phase G5 (localhost HTTP) fail

- Abort Option B unified HTTP
- Revise spec: keep stdio default cho local, HTTP only cho remote self-host
- Daemon concept retained cho resource sharing nhưng accessed via stdio proxy luôn
- Re-estimate Phase I/J

### Nếu Phase J migration causes regression

- Revert `mcp-core` to v1.x (restore backup)
- Revert dependent repos to previous version
- Publish old versions back to stable channel
- Investigate root cause, redesign

### Nếu Phase L reveals real-PR from human contributor không rebase-able

- Keep PR open, communicate delay
- Adapt design nếu feedback valid

### Nếu Phase M E2E reveals fundamental architecture issues

- Block release
- Fix root cause trong respective phase (I/J/K)
- Re-run M

---

## Task tracker summary

| Phase | Tasks | Size | Dependencies | Critical |
|-------|-------|------|--------------|----------|
| G | 6 | M-L | — | P0 blocker |
| H | 5 | M | — | P0 user-visible bug |
| I | 7 | XL | G done | Phase J blocker |
| J | 7 | XL | I done | Core work |
| K | 5 | M-L | J mostly done | Release gate |
| L | 5 | XL | — (parallel) | Release gate |
| M | 9 | XL | All done | Final |

**Total estimated**: 4-6 tuần full-time (single person). Parallel tracks có thể rút ngắn.

---

## Evidence requirement (reminder)

Mỗi task marked complete phải attach:
- `gh api` hoặc `gh pr view` hoặc `gh run view` output
- `git log --oneline -1` hash
- File path + line number nếu code change
- Test command + stdout

Tránh lặp lại incident session Antigravity/cf5ac4a3 hallucinate "done" mà không verify.

---

## Open questions (references spec §6)

1. Agent auto-open browser on 401 — resolve in G5
2. Shared ONNX across wet+mnemo+crg daemons — defer, phase sau
3. Stdio proxy auto-ensure race — atomic file lock pattern in I3
4. PSR prefix config — resolve in K4
5. Notion current state — resolve in G6
6. Idle shutdown policy — default never, configurable via env, decide in I3
