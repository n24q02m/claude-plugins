# P4: Finalize — Gemini Cleanup + Docs Validation + Security Audit + Marketplace Sync + Release

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove deprecated Gemini CLI artifacts, validate all docs, audit stdio/HTTP security model, sync marketplace, prepare stable release for all 8 repos.

**Architecture:** 7 source repos cleanup (parallel) -> docs cross-check -> security audit -> marketplace sync -> release prep -> verification.

**Tech Stack:** git, gh CLI, PSR v10, npm, PyPI, Docker, bash

**Spec:** `docs/superpowers/specs/2026-04-01-e2e-mcp-plugin-testing-design.md` Sections 6, 8

**Depends on:** P0 DONE, P1 DONE, P2 Code DONE, P3 Partial (godot DONE, email/notion code done)

**Repos:** All 8 + claude-plugins:
- `mcp-relay-core` (v1.2.0 stable, no changes needed)
- `wet-mcp` (v2.19.0 stable)
- `mnemo-mcp` (v1.14.0 stable)
- `better-code-review-graph` (v3.4.0 stable)
- `better-godot-mcp` (v1.9.1 stable)
- `better-telegram-mcp` (v3.5.0 + 6 unreleased commits with breaking changes)
- `better-email-mcp` (v1.17.0 + 12 unreleased commits)
- `better-notion-mcp` (v2.22.1 + 25 unreleased commits)
- `claude-plugins` (marketplace, stale)

---

### Task 1: Remove Gemini CLI artifacts from 4 Python source repos

**Context:** Gemini CLI deprecated 02/04/2026 per plugin-audit-plan. All repos still have `gemini-extension.json`, PSR version_variables referencing it, README "Gemini CLI" section, and "gemini-cli" keyword.

**Repos:** wet-mcp, mnemo-mcp, better-code-review-graph, better-telegram-mcp

**Files per repo:**
- Delete: `gemini-extension.json`
- Modify: `README.md` (remove Gemini CLI Extension section)
- Modify: `pyproject.toml` (remove "gemini-cli" from keywords, remove "gemini-extension.json:version" from version_variables)

- [ ] **Step 1: wet-mcp — Delete gemini-extension.json**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
rm gemini-extension.json
```

- [ ] **Step 2: wet-mcp — Edit pyproject.toml**

Remove `"gemini-cli"` from keywords array (line 8).
Remove `"gemini-extension.json:version"` from version_variables (line 124).

- [ ] **Step 3: wet-mcp — Edit README.md**

Remove the "Gemini CLI Extension" setup subsection (the block with `gemini extensions install` command).

- [ ] **Step 4: wet-mcp — Commit**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
git add gemini-extension.json pyproject.toml README.md
git commit -m "feat: remove deprecated Gemini CLI extension support

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 5: Repeat Steps 1-4 for mnemo-mcp**
- [ ] **Step 6: Repeat Steps 1-4 for better-code-review-graph**
- [ ] **Step 7: Repeat Steps 1-4 for better-telegram-mcp**

---

### Task 2: Remove Gemini CLI artifacts from 3 TypeScript source repos

**Repos:** better-godot-mcp, better-email-mcp, better-notion-mcp

**Files per repo:**
- Delete: `gemini-extension.json`
- Modify: `README.md` (remove Gemini CLI Extension section)
- Modify: `package.json` (remove "gemini-cli" from keywords)
- Modify: `semantic-release.toml` (remove "gemini-extension.json:version" from version_variables)

- [ ] **Step 1: better-godot-mcp — Delete + Edit + Commit**

```bash
cd /c/Users/n24q02m-wlap/projects/better-godot-mcp
rm gemini-extension.json
# Edit package.json: remove "gemini-cli" from keywords
# Edit semantic-release.toml: remove gemini-extension.json:version
# Edit README.md: remove Gemini CLI section
git add -A && git commit -m "feat: remove deprecated Gemini CLI extension support"
```

- [ ] **Step 2: Repeat for better-email-mcp**
- [ ] **Step 3: Repeat for better-notion-mcp**

---

### Task 3: Cross-check docs for all 7 servers

For each server, verify the 5-point consistency matrix:

```
CLAUDE.md <-> README.md <-> relay_schema <-> server code <-> plugin.json
```

**Check per repo:**
- [ ] Tool/action list in README matches actual server code
- [ ] Env var list in README matches actual config
- [ ] Setup commands work (uvx/npx correct package names)
- [ ] Relay form fields match relay_schema code
- [ ] Plugin.json description accurate
- [ ] marketplace.json description matches

**Findings from audit (already verified):**

| Repo | Tool/Action Match | Env Vars | Setup Commands | Relay Schema |
|------|-------------------|----------|----------------|--------------|
| wet-mcp | MATCH (6 tools) | OK (28 vars) | OK | OK |
| mnemo-mcp | MATCH (3 tools) | OK (23 vars) | OK | OK |
| crg | MATCH (5 tools) | OK (4 core vars) | OK | OK |
| godot | MATCH (17 tools) | OK | OK | N/A (no relay) |
| telegram | MATCH (6 tools) | OK (7 vars) | OK | OK (2 modes) |
| email | MATCH (5 tools, 15 actions) | OK | OK | OK |
| notion | MATCH (9 tools, 39 actions) | OK | OK | OK |

- [ ] **Step 1: Verify marketplace.json descriptions are accurate**

Current marketplace descriptions to check:
- `better-godot-mcp`: "18 tools" but actual is 17 tools -> FIX
- `better-telegram-mcp`: "Bot API" only but now has MTProto too -> FIX

- [ ] **Step 2: Fix marketplace.json mismatches**

---

### Task 4: Security audit — Stdio single-user vs HTTP multi-user

**Goal:** Document and verify that stdio relay serves single-user, HTTP relay serves multi-user, without security violations.

- [ ] **Step 1: Audit mcp-relay-core security model**

**Stdio mode** (`packages/relay-server/src/local.ts`):
- Ephemeral Express server on random localhost port
- Serves relay pages from local directory
- Only accessible from localhost
- Session TTL 10 minutes, max 10 sessions/IP
- One-shot credential consumption (409 on resubmit)
- Zero-knowledge: relay never sees plaintext (ECDH P-256 + AES-256-GCM)
- Config stored locally: `~/.config/mcp/config.enc` (machine-bound key)
- **Verdict: SECURE for single-user**

**HTTP mode** (production relay server):
- Rate limiting: 30/min mutations, 120/min polling per IP
- Session TTL 10 minutes with auto-cleanup
- Max 10 sessions per IP
- Max 50 messages + 50 responses per session
- Trust proxy for CF Tunnel/Caddy IP extraction
- Same zero-knowledge encryption as stdio
- **Verdict: SECURE for multi-user**

- [ ] **Step 2: Audit per-server HTTP multi-user implementations**

**better-telegram-mcp** (`transports/http_multi_user.py`):
- DCR (Dynamic Client Registration) with HMAC-derived credentials
- Per-user bearer token authentication
- Per-request backend injection via ContextVar
- Session ownership: `session_owners[session_id] = bearer`
- Rate limiting: 120 req/min MCP, 20 req/min auth
- 30-day session persistence with concurrent restoration
- Bot mode: validate token with Telegram getMe
- User mode: OTP + optional 2FA
- **Verdict: SECURE for multi-user**

**better-email-mcp** (`transports/http.ts`):
- DCR (stateless HMAC-based)
- OAuth 2.1 + PKCE S256 authorization flow
- Per-user credential encryption: AES-256-GCM, PBKDF2 key
- Per-user account isolation: `userAccounts: Map<userId, AccountConfig[]>`
- Session ownership: `sessionOwners: Map<sessionId, userId>`
- Bearer token with 24h TTL
- IMAP validation before credential storage
- Rate limiting: 120 req/min MCP, 20 req/min auth
- **Verdict: SECURE for multi-user**

**better-notion-mcp** (`transports/http.ts`):
- OAuth 2.1 + PKCE S256 with Notion OAuth
- Stateless DCR
- Per-session Notion token binding
- Session ownership: cross-user hijacking blocked (403)
- IP-scoped pending binds (30s TTL, one-shot)
- Verification cache (5 min TTL)
- Rate limiting: 120 req/min MCP, 20 req/min auth
- **Verdict: SECURE for multi-user**

- [ ] **Step 3: Document findings in spec**

Add security audit section to the spec document.

---

### Task 5: Marketplace sync

- [ ] **Step 1: Run sync script**

```bash
cd /c/Users/n24q02m-wlap/projects/claude-plugins
bash scripts/sync-plugins.sh
```

- [ ] **Step 2: Remove gemini-extension.json from marketplace copies**

```bash
for plugin in wet-mcp mnemo-mcp better-notion-mcp better-email-mcp better-godot-mcp better-telegram-mcp better-code-review-graph; do
  rm -f plugins/$plugin/gemini-extension.json
done
```

- [ ] **Step 3: Verify plugin.json versions match source repos**

```bash
for plugin in wet-mcp mnemo-mcp better-notion-mcp better-email-mcp better-godot-mcp better-telegram-mcp better-code-review-graph; do
  echo "=== $plugin ==="
  diff <(python -m json.tool plugins/$plugin/.claude-plugin/plugin.json) \
       <(python -m json.tool /c/Users/n24q02m-wlap/projects/$plugin/.claude-plugin/plugin.json) 2>/dev/null
done
```

- [ ] **Step 4: Remove Gemini references from marketplace README**

- [ ] **Step 5: Commit marketplace**

```bash
git add -A
git commit -m "feat: sync plugins, remove Gemini CLI artifacts

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

---

### Task 6: Update spec with completion status

- [ ] **Step 1: Update spec document**

Update `docs/superpowers/specs/2026-04-01-e2e-mcp-plugin-testing-design.md` with:
- Phase completion status (Pre, P0-P4)
- Security audit results
- Release version tracking
- Outstanding items (releases pending CI/CD)

---

### Task 7: Release preparation and verification plan

**Repos needing stable release (have unreleased commits):**

| Repo | Last stable | Unreleased commits | Expected next |
|------|------------|-------------------|---------------|
| better-telegram-mcp | v3.5.0 | 6 (breaking: tool redesign + HTTP multi-user) | v4.0.0 |
| better-email-mcp | v1.17.0 | 12 (HTTP relay migration, security, perf) | v1.18.0 |
| better-notion-mcp | v2.22.1 | 25+ (bug fixes, security, test coverage) | v2.23.0 |
| wet-mcp | v2.19.0 | +Gemini cleanup commit | v2.20.0 |
| mnemo-mcp | v1.14.0 | +Gemini cleanup commit | v1.15.0 |
| crg | v3.4.0 | +Gemini cleanup commit | v3.5.0 |
| godot | v1.9.1 | +Gemini cleanup commit | v1.10.0 |

- [ ] **Step 1: Push all repos to main**

```bash
for repo in wet-mcp mnemo-mcp better-code-review-graph better-godot-mcp better-telegram-mcp better-email-mcp better-notion-mcp; do
  echo "=== $repo ==="
  cd /c/Users/n24q02m-wlap/projects/$repo
  git push origin main
done
```

- [ ] **Step 2: Trigger CD workflows**

```bash
for repo in wet-mcp mnemo-mcp better-code-review-graph better-godot-mcp better-telegram-mcp better-email-mcp better-notion-mcp; do
  cd /c/Users/n24q02m-wlap/projects/$repo
  gh workflow run cd.yml 2>/dev/null || echo "No cd.yml for $repo"
done
```

- [ ] **Step 3: Verify published packages**

```bash
# Python
pip index versions wet-mcp
pip index versions mnemo-mcp
pip index versions better-code-review-graph
pip index versions better-telegram-mcp

# TypeScript
npm view @n24q02m/better-godot-mcp version
npm view @n24q02m/better-email-mcp version
npm view @n24q02m/better-notion-mcp version
```

- [ ] **Step 4: Post-release marketplace re-sync**

After all releases complete, re-run sync-plugins.sh to pick up new versions.

- [ ] **Step 5: Verify plugin install**

```
/plugin marketplace add n24q02m/claude-plugins
/plugin install wet-mcp@n24q02m-plugins
/plugin install mnemo-mcp@n24q02m-plugins
/plugin install better-notion-mcp@n24q02m-plugins
/plugin install better-email-mcp@n24q02m-plugins
/plugin install better-godot-mcp@n24q02m-plugins
/plugin install better-telegram-mcp@n24q02m-plugins
/plugin install better-code-review-graph@n24q02m-plugins
```
