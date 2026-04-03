# Consolidated Issue/PR Resolution + Full Live E2E Testing

**Ngay**: 2026-04-03
**Scope**: 11 repos, 296 open PRs, 22 open issues, full live E2E testing
**Goal**: Resolve ALL open issues/PRs across 11 repos via consolidated per-repo PRs, then verify everything with full live E2E tests

---

## 1. Inventory

### 1.1 Per-repo breakdown

| # | Repo | Open Issues | Open PRs | Sentinel | Bolt | TEST | Other (FIX/CLEANUP/deps) |
|---|------|-------------|----------|----------|------|------|--------------------------|
| 1 | qwen3-embed | 1 | 31 | 4 | 3 | 8 | 16 |
| 2 | mcp-relay-core | 1 | 50 | 7 | 7 | 8 | 28 |
| 3 | wet-mcp | 4 | 51 | 6 | 7 | 21 | 17 |
| 4 | mnemo-mcp | 3 | 37 | 1 | 3 | 4 | 29 |
| 5 | better-code-review-graph | 3 | 43 | 6 | 6 | 7 | 24 |
| 6 | better-telegram-mcp | 3 | 34 | 3 | 2 | 19 | 10 |
| 7 | better-godot-mcp | 1 | 28 | 4 | 8 | 5 | 11 |
| 8 | better-email-mcp | 3 | 0 | 0 | 0 | 0 | 0 |
| 9 | better-notion-mcp | 2 | 1 | 0 | 0 | 0 | 1 (OyaAIProd, skip) |
| 10 | claude-plugins | 1 | 21 | 9 | 4 | 3 | 5 |
| 11 | n24q02m | 0 | 0 | 0 | 0 | 0 | 0 |
| | **Total** | **22** | **296** | **40** | **40** | **75** | **141** |

### 1.2 Issue types

**Core dependency updates (n24q02m-ci bot):**
- `mcp-relay-core` to 1.2.0: wet #668, mnemo #320, crg #114, telegram #134, email #300, notion #367
- `qwen3-embed` to 1.6.0: wet #666, mnemo #319, crg #113
- `n24q02m-web-core` to 1.0.1: wet #667

**Feature requests (self-created, likely already implemented):**
- telegram #74: Relay E2E encryption
- email #241: Relay setup

**Renovate Dashboard:** 1 per repo (auto-managed, no action needed)

### 1.3 PR sources

- **Jules suggestions**: Sentinel (security), Bolt (performance), TEST (coverage), FIX (code quality), CLEANUP (unused code, broad exceptions)
- **Renovate/Dependabot**: Dependency updates (docker digests, lock file, non-major deps)
- **OyaAIProd**: SafeSkill badge on notion #366 -- SKIP (per user decision)

### 1.4 Repos with 0 open PRs (no Jules work needed)

- `better-email-mcp`: 0 PRs, only dependency issues
- `better-notion-mcp`: 1 PR (OyaAIProd, skip), only dependency issues
- `n24q02m`: 0 issues, 0 PRs

---

## 2. Strategy

### 2.1 Per-repo consolidated approach

For each repo (in dependency order):

```
Phase A: REVIEW
  1. Fetch all open PRs
  2. For each PR:
     - Read the diff
     - Classify: ACCEPT (valid fix) / REJECT (wrong, outdated, or already fixed)
     - Note: accepted changes to implement
  3. For each open issue:
     - Check if already resolved on main
     - If yes: close with reference
     - If no: plan fix

Phase B: IMPLEMENT
  1. Create single branch: fix/consolidated-jules-review
  2. Implement ALL accepted changes in logical commits
  3. Update dependencies (mcp-relay-core, qwen3-embed, web-core)
  4. Run full test suite
  5. Create 1 consolidated PR

Phase C: CLOSE
  1. Merge consolidated PR
  2. Bulk close all Jules PRs (reference consolidated PR)
  3. Close Renovate/Dependabot PRs (superseded by consolidated PR)
  4. Close dependency issues (resolved in consolidated PR)
  5. Close feature issues (if already implemented)

Phase D: RELEASE
  1. Trigger CD stable release
  2. Verify published package version
```

### 2.2 Review criteria by category

**Sentinel (Security) -- HIGH priority, review carefully:**
- SQL injection: ACCEPT if using string formatting in queries, REJECT if already parameterized
- Path traversal: ACCEPT if real risk, REJECT if already validated
- TOCTOU: ACCEPT if race condition is exploitable
- CORS/rate limit: ACCEPT if misconfigured
- Hardcoded secrets/salts: ACCEPT if real secret, REJECT if intentional constant

**Bolt (Performance) -- MEDIUM priority:**
- N+1 queries: ACCEPT if measurable impact
- O(N^2) algorithms: ACCEPT if data size warrants
- Memory optimization: ACCEPT if significant
- Micro-optimizations (string concat in loop, chained array methods): REJECT unless hot path

**TEST (Missing tests) -- MEDIUM priority, selective:**
- Error path tests: ACCEPT if testing real error scenarios
- Edge case tests: ACCEPT if covering important edge cases
- Redundant/trivial tests: REJECT (e.g., testing obvious getters)

**FIX (Code quality) -- LOW priority, selective:**
- Too many parameters: ACCEPT only if > 8 params and refactor is clean
- Deeply nested blocks: ACCEPT only if > 4 levels and refactor improves readability
- Long functions: ACCEPT only if > 100 lines and natural split point exists

**CLEANUP -- LOW priority, selective:**
- Unused functions: ACCEPT if truly unused (grep confirms 0 callers)
- Broad exception catching: REJECT most (intentional catch-all is fine for MCP tools)
- Console.log in production: ACCEPT for backend, REJECT for intentional debug

**Renovate/Dependabot -- ACCEPT if CI passes:**
- Lock file maintenance: ACCEPT
- Docker digest updates: ACCEPT
- Major version bumps: REVIEW carefully (breaking changes)

### 2.3 Dependency order

```
qwen3-embed (upstream, no deps on our repos)
  |
  +-- mcp-relay-core (no deps on qwen3, but process first for relay updates)
  |
  +-- wet-mcp (depends on qwen3 + relay + web-core)
  +-- mnemo-mcp (depends on qwen3 + relay)
  +-- better-code-review-graph (depends on qwen3 + relay)
  +-- better-telegram-mcp (depends on relay)
  |
  +-- better-godot-mcp (depends on relay npm -- but no relay support, just npm package)
  +-- better-email-mcp (depends on relay npm)
  +-- better-notion-mcp (depends on relay npm)
  |
  +-- claude-plugins (depends on all 7 servers)
  +-- n24q02m (standalone)
```

### 2.4 Parallelization

Repos within the same dependency tier can be processed in parallel:
- Tier 1: qwen3-embed (1 repo)
- Tier 2: mcp-relay-core (1 repo)
- Tier 3: wet-mcp + mnemo-mcp + crg + telegram (4 repos, parallel)
- Tier 4: godot + email + notion (3 repos, parallel)
- Tier 5: claude-plugins + n24q02m (2 repos, parallel)
- Tier 6: Full live E2E testing (sequential, requires credentials)

---

## 3. Per-Repo Scope

### 3.1 qwen3-embed (31 PRs, 1 issue)

**Issue**: Renovate Dashboard only.

**PRs by category:**
- Security (4): eval(), path traversal tar, missing verify=True, tarfile symlinks
- Performance (3): uncached string lowercasing, normalize in-place, numpy tensor pooling
- Tests (8): file metadata, cache checking, download_file, punctuation, cache_dir, alphanumeric, worker exceptions
- Fix (16): too many parameters (multiple), overly long function, dataclass refactor

**Expected outcome:** ~15-20 accepted changes, mostly security fixes + key tests.

### 3.2 mcp-relay-core (50 PRs, 1 issue)

**Issue**: Renovate Dashboard only.

**PRs by category:**
- Security (7): PBKDF2 iterations, CORS, input size validation, trust proxy, rate limit IP, schema size
- Performance (7): session counting O(1), polling filter, config I/O, optimizer
- Tests (8): startLocalRelay, retry, error paths, form skip/submit
- Fix (28): long functions, code duplication, console.log, PSR release, npm publish, PyPI publish, base64url

**Expected outcome:** ~20-25 accepted changes. Security + performance + cleanup of frontend code.

### 3.3 wet-mcp (51 PRs, 4 issues)

**Issues**: mcp-relay-core 1.2.0, web-core 1.0.1, qwen3-embed 1.6.0, Renovate Dashboard.

**PRs by category:**
- Security (6): SQL injection (4 variants in db.py), other
- Performance (7): JSON parsing, async I/O, SQLite batch, N+1 sitemap
- Tests (21): relay_setup, db.py, security.py, setup_tool, embedder, sync, token_store, crawler, docs
- Fix (17): refactor extract/media params, unused functions, randomize offset

**Expected outcome:** ~25-30 accepted changes. SQL injection fixes critical. Dependency updates.

### 3.4 mnemo-mcp (37 PRs, 3 issues)

**Issues**: mcp-relay-core 1.2.0, qwen3-embed 1.6.0, Renovate Dashboard.

**PRs by category:**
- Security (1): SQL injection in table creation
- Performance (3): N+1 queries (FTS, graph, upsert)
- Tests (4): config GGUF, embedding init, token store chmod, GPU detection
- Fix (29): mostly Broad Exception Catching (~20), N+1 query fixes, fixtures, string concat

**Expected outcome:** ~10-15 accepted changes. Most CLEANUP/broad-exception will be rejected.

### 3.5 better-code-review-graph (43 PRs, 3 issues)

**Issues**: mcp-relay-core 1.2.0, qwen3-embed 1.6.0, Renovate Dashboard.

**PRs by category:**
- Security (6): SQL injection (3 variants), input length limits (DoS)
- Performance (6): N+1 queries, brute-force cosine, semantic search, graph queries
- Tests (7): find_large_functions, error tests, store init, changed_files, binary check
- Fix (24): deeply nested blocks (~12), overly complex functions, refactor query_graph, deps

**Expected outcome:** ~20-25 accepted changes. Security + performance critical.

### 3.6 better-telegram-mcp (34 PRs, 3 issues)

**Issues**: mcp-relay-core 1.2.0, relay feature #74, Renovate Dashboard.

**PRs by category:**
- Security (3): TOCTOU session file, hardcoded salt, insecure bind 0.0.0.0
- Performance (2): sync os.chmod, sync file write
- Tests (19): edge cases, exception handling, auth_client, auth_server, relay_setup
- Fix (10): CLI typer, too many params, long function, rate limiting, deps

**Expected outcome:** ~15-20 accepted changes. Security fixes + selected tests.

### 3.7 better-godot-mcp (28 PRs, 1 issue)

**Issue**: Renovate Dashboard only.

**PRs by category:**
- Security (4): INI injection, binary execution, process termination, ReDoS
- Performance (8): input map parsing, array chaining, string slicing, regex, rename
- Tests (5): escapeRegExp, findClosestMatch, throwUnknownAction, headless, init-server
- Fix (11): unused functions (writeScene, getNodePath, execGodotScript, etc.), type checks, deps

**Expected outcome:** ~15-18 accepted changes.

### 3.8 better-email-mcp (0 PRs, 3 issues)

**Issues**: mcp-relay-core 1.2.0, relay feature #241, Renovate Dashboard.

**Expected outcome:** Close dependency issue (already updated). Close #241 if relay already implemented. No PR work.

### 3.9 better-notion-mcp (1 PR, 2 issues)

**Issues**: mcp-relay-core 1.2.0, Renovate Dashboard.
**PR**: OyaAIProd SafeSkill badge #366 -- CLOSE.

**Expected outcome:** Close dependency issue. Close OyaAIProd PR. No implementation work.

### 3.10 claude-plugins (21 PRs, 1 issue)

**Issue**: Renovate Dashboard only.

**PRs by category:**
- Security (9): command injection in CD (4 CRITICAL), code injection, data exfiltration, unsafe python -c
- Performance (4): subshell in loop, memory-efficient dir check
- Tests (3): session-start.sh hook, edge cases
- Fix (5): duplicate sync logic, inline Python scripts, deps

**Expected outcome:** ~12-15 accepted changes. CRITICAL security fixes in CD workflow urgent.

### 3.11 n24q02m (0 issues, 0 PRs)

**Expected outcome:** No work needed. Verify profile README is current.

---

## 4. Full Live E2E Testing

After all repos are resolved and released:

### 4.1 Test matrix

| Server | relay mode | env mode | plugin mode | HTTP mode |
|--------|-----------|----------|-------------|-----------|
| wet-mcp | Manual (API keys) | Automated | Automated | N/A |
| mnemo-mcp | Manual (API keys) | Automated | Automated | N/A |
| crg | Manual (API keys) | Automated | Automated | N/A |
| telegram (bot) | Manual (BOT_TOKEN) | Automated | Automated | Manual |
| telegram (user) | Manual (OTP+2FA) | Manual | Manual | Manual |
| godot | N/A | Automated | Automated | N/A |
| email (Gmail) | Manual (app password) | Automated | Automated | Manual |
| email (Outlook) | Manual (OAuth DCF) | Manual | Manual | Manual |
| notion (stdio) | Manual (NOTION_TOKEN) | Automated | Automated | N/A |
| notion (HTTP) | N/A | N/A | N/A | Manual (OAuth PKCE) |

### 4.2 Required credentials (user provides)

- Telegram: BOT_TOKEN + phone number (user mode)
- Email: Gmail app password + Outlook account
- Notion: NOTION_TOKEN (integration token)
- Embedding APIs: JINA_AI_API_KEY, GEMINI_API_KEY (optional)

### 4.3 Test procedure per server

```
1. Start server from source (uv run / npx)
2. Connect via MCP protocol (ClientSession + stdio_client)
3. Verify: server_init (name, version, capabilities)
4. Verify: tools/list (count, names match spec)
5. Test EVERY tool action with real data
6. Verify: error handling (invalid action, missing params)
7. Repeat for each setup mode (relay, env, plugin)
```

### 4.4 Acceptance criteria

- ALL tools/actions return valid results (no errors, no timeouts)
- Relay setup works on Chrome (auto-open browser, user enters creds, server receives config)
- Plugin mode works with published packages (uvx/npx from PyPI/npm)
- HTTP mode works for telegram, email, notion (multi-user sessions)
- 0 regressions: existing unit/integration tests pass

---

## 5. Execution Plan Summary

| Phase | Repos | Sessions | Deliverable |
|-------|-------|----------|-------------|
| 1 | qwen3-embed | 1 | 1 consolidated PR + release |
| 2 | mcp-relay-core | 1 | 1 consolidated PR + release |
| 3 | wet + mnemo + crg + telegram | 2-3 | 4 consolidated PRs + releases |
| 4 | godot + email + notion | 1-2 | 1-3 consolidated PRs + releases |
| 5 | claude-plugins + n24q02m | 1 | 1 consolidated PR + marketplace sync |
| 6 | Full live E2E testing | 1-2 | Test report, all modes verified |

**Estimated total: 7-10 sessions**

### 5.1 Done criteria

| Criterion | Check |
|-----------|-------|
| 0 open issues (except Renovate Dashboard) | `gh issue list --state open` per repo |
| 0 open PRs (except Renovate Dashboard) | `gh pr list --state open` per repo |
| All Jules PRs reviewed and closed | Bulk close with consolidated PR reference |
| All dependency issues resolved | mcp-relay-core, qwen3-embed, web-core updated |
| All unit/integration tests pass | CI green on all repos |
| Full live E2E testing complete | All servers, all modes, all tools verified |
| Stable releases published | PyPI + npm + Docker for all servers |
| Marketplace synced | claude-plugins with latest versions |
