# Consolidated Issue/PR Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve ALL 296 open PRs + 22 open issues across 11 repos via consolidated per-repo PRs, then full live E2E testing.

**Architecture:** Per-repo: review all Jules PRs (read diffs, accept/reject) -> implement accepted changes in single branch -> update deps -> test -> merge -> bulk close -> release. Repos processed in dependency order.

**Tech Stack:** git, gh CLI, Python (uv), TypeScript (bun/npx), PSR v10 CD workflows

**Spec:** `docs/superpowers/specs/2026-04-03-consolidated-issue-pr-resolution-design.md`

**IMPORTANT RULES:**
- Commit prefix: ONLY `fix:` or `feat:`. NEVER `chore:`, `docs:`, `refactor:`, `ci:`.
- NEVER skip pre-commit hooks (`--no-verify`).
- NEVER close PRs/issues without reviewing them first.
- Each repo produces exactly 1 consolidated PR containing ALL accepted changes.

---

## Process Template (applied to each repo)

Every task below follows this exact process. The per-repo sections specify which PRs/issues to review and what dependencies to update.

### Phase A: Review

```bash
# 1. List all open PRs with diffs
cd /c/Users/n24q02m-wlap/projects/<REPO>
unset GITHUB_TOKEN
gh pr list --state open --limit 500 --json number,title,labels

# 2. For each PR, review the diff:
gh pr diff <NUMBER> | head -200

# 3. Classify each PR: ACCEPT / REJECT / ALREADY-FIXED
# Record decisions in a local file for reference
```

**Review criteria (from spec section 2.2):**
- **Sentinel/Security**: ACCEPT if real vulnerability. REJECT if false positive or already mitigated.
- **Bolt/Performance**: ACCEPT if measurable impact on hot path. REJECT micro-optimizations.
- **TEST**: ACCEPT error path + edge case tests. REJECT trivial/redundant tests.
- **FIX**: ACCEPT if > 8 params or > 4 nesting levels. REJECT cosmetic refactors.
- **CLEANUP**: ACCEPT truly unused code (grep confirms). REJECT broad-exception changes (intentional).
- **Renovate/Deps**: ACCEPT if CI passes. REVIEW major version bumps carefully.

### Phase B: Implement

```bash
# 1. Create consolidated branch
git checkout main && git pull origin main
git checkout -b fix/consolidated-jules-review

# 2. Implement ALL accepted changes (cherry-pick or manual)
# 3. Update dependencies (mcp-relay-core, qwen3-embed, web-core)
# 4. Run tests
uv run pytest --tb=short -q   # Python repos
npx vitest run                  # TypeScript repos

# 5. Commit
git add -A
git commit -m "fix: resolve Jules PR review findings + update dependencies

Accepted N of M Jules suggestions. Updated deps.
Closes #X, #Y, #Z.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### Phase C: PR + Close

```bash
# 1. Push and create consolidated PR
git push -u origin fix/consolidated-jules-review
gh pr create --title "fix: consolidated Jules PR review + dependency updates" --body "..."

# 2. Merge (after CI passes)
gh pr merge --squash --auto

# 3. Bulk close Jules PRs
for pr in <PR_NUMBERS>; do
  gh pr close $pr --comment "Reviewed and addressed in consolidated PR #<CONSOLIDATED>. See review notes."
done

# 4. Close resolved issues
for issue in <ISSUE_NUMBERS>; do
  gh issue close $issue --comment "Resolved in consolidated PR #<CONSOLIDATED>."
done
```

### Phase D: Release

```bash
git checkout main && git pull origin main
gh workflow run CD -f release_type=stable
# Verify: gh run list --workflow=CD --limit=1
```

---

## Task 1: qwen3-embed (31 PRs, 1 issue)

**Repo:** `C:/Users/n24q02m-wlap/projects/qwen3-embed`
**Why first:** Upstream dependency for wet-mcp, mnemo-mcp, better-code-review-graph.

**Open Issues:**
- #107 Renovate Dashboard (no action, auto-managed)

**Open PRs to review (31):**

| # | Title | Category |
|---|-------|----------|
| 360 | Use of eval() on user input | SECURITY |
| 348 | Missing verify=True in requests.get | SECURITY |
| 339 | Fix path traversal via tar archive symlinks | SECURITY |
| 336 | Fix path traversal vulnerability in tarfile symlinks | SECURITY |
| 353 | Path Traversal vulnerability in tarfile extraction | SECURITY |
| 354 | Uncached string lowercasing in model name resolution | PERF |
| 340 | Optimize normalize function with in-place memory ops | PERF |
| 335 | Optimize Numpy tensor operations for pooling | PERF |
| 358 | Test missing llama_cpp library | TEST |
| 350 | Test file metadata saving failure | TEST |
| 349 | Test cache checking failure | TEST |
| 346 | Test download_file_from_gcs function | TEST |
| 344 | Test get_all_punctuation | TEST |
| 343 | Test define_cache_dir edge cases | TEST |
| 342 | Test remove_non_alphanumeric | TEST |
| 341 | Test parallel worker exception handling | TEST |
| 365, 363 | Too many parameters in _load_onnx_model | FIX (duplicate) |
| 364 | Refactor ParallelWorkerPool to use dataclasses | FIX |
| 362, 361, 359, 357, 356, 355, 352, 351, 347, 345 | Too many params / overly long function | FIX |
| 338 | fix(deps): update non-major dependencies | DEPS |
| 337 | chore(deps): update qodo-ai/pr-agent digest | DEPS |

**Dependencies to update:** None (this IS the upstream).

- [ ] **Step 1: Review all 31 PRs**

```bash
cd /c/Users/n24q02m-wlap/projects/qwen3-embed
unset GITHUB_TOKEN
for pr in 360 348 339 336 353 354 340 335 358 350 349 346 344 343 342 341 365 363 364 362 361 359 357 356 355 352 351 347 345 338 337; do
  echo "=== PR#$pr ===" && gh pr diff $pr 2>/dev/null | head -100 && echo ""
done
```

Review each diff. Classify ACCEPT/REJECT per criteria in Process Template.

- [ ] **Step 2: Create branch and implement accepted changes**

```bash
git checkout main && git pull origin main
git checkout -b fix/consolidated-jules-review
# Implement accepted security fixes, tests, perf improvements
# Skip: duplicate PRs, cosmetic "too many params" refactors that don't improve safety
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest --tb=short -q
```

Expected: ALL pass, 0 failures.

- [ ] **Step 4: Commit and create PR**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix: resolve Jules PR findings — security fixes + tests + perf

- Fix eval() on user input (#360)
- Fix path traversal in tarfile (#339, #336, #353)
- Add verify=True to requests.get (#348)
- Add tests for edge cases (#358, #350, #349, #346, #344, #343, #342, #341)
- Optimize normalize/pooling operations (#340, #335)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u origin fix/consolidated-jules-review
gh pr create --title "fix: consolidated Jules PR review" --body "Reviewed 31 open PRs. Accepted N, rejected M. See commit for details."
```

- [ ] **Step 5: Merge and bulk close**

```bash
# After CI passes:
gh pr merge --squash --auto
# Bulk close all Jules PRs:
for pr in 360 348 339 336 353 354 340 335 358 350 349 346 344 343 342 341 365 363 364 362 361 359 357 356 355 352 351 347 345 338 337; do
  gh pr close $pr --comment "Reviewed in consolidated PR. Accepted findings implemented; rejected items documented in review."
done
```

- [ ] **Step 6: Release**

```bash
git checkout main && git pull origin main
gh workflow run CD -f release_type=stable
```

---

## Task 2: mcp-relay-core (50 PRs, 1 issue)

**Repo:** `C:/Users/n24q02m-wlap/projects/mcp-relay-core`
**Why second:** Upstream dependency for all 7 MCP servers.

**Open Issues:**
- #1 Renovate Dashboard (no action)

**Open PRs to review (50):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY | #79 (PBKDF2), #63 (CORS), #59 (input size), #65 (rate limit IP), #82 (CORS+schema), #49 (trust proxy), #33 (IP spoofing), #37 (CORS), #38 (schema size) | 9 |
| PERF | #81 (session count), #73 (session count), #67 (polling), #53 (polling filter), #48 (IP rate limit O(1)), #40 (config I/O), #32 (cache key), #31 (O(1) session) | 8 |
| TEST | #76 (form skip), #71 (form submit), #69 (passphrase key), #61 (retry), #41 (cleanup), #35 (localRelay), #34 (deleteSession) | 7 |
| FIX/CLEANUP | #80 (PSR Python), #78 (console.log), #77 (code dup), #75 (code dup), #74 (console.log), #72 (npm publish), #70 (async config), #68 (PSR JS), #66 (PyPI publish), #64 (console.log), #62 (base64url), #60 (console.log backend), #58 (long fn), #57 (exports), #56 (long fn), #55 (long fn), #54 (a11y), #50 (a11y), #39 (PyPI), #36 (unused import) | 20 |
| UX | #83 (Palette UX) | 1 |
| DEPS | #52 (TS v6), #51 (@types/node v25), #47 (non-major), #46 (semgrep), #45 (pr-agent) | 5 |

- [ ] **Step 1: Review all 50 PRs**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
unset GITHUB_TOKEN
for pr in 83 82 81 80 79 78 77 76 75 74 73 72 71 70 69 68 67 66 65 64 63 62 61 60 59 58 57 56 55 54 53 52 51 50 49 48 47 46 45 41 40 39 38 37 36 35 34 33 32 31; do
  echo "=== PR#$pr ===" && gh pr view $pr --json title -q '.title' && gh pr diff $pr 2>/dev/null | head -80 && echo ""
done
```

- [ ] **Step 2: Implement accepted changes on branch**

```bash
git checkout main && git pull origin main
git checkout -b fix/consolidated-jules-review
# Priority: security (CORS, PBKDF2, input validation, rate limit)
# Then: perf (session counting, polling)
# Then: selected tests + cleanup (console.log, code dup)
# Skip: PSR/publish PRs (already working), cosmetic refactors, major deps (TS v6)
```

- [ ] **Step 3: Run tests**

```bash
cd packages/core-ts && npm test
cd ../relay-server && npm test
cd ../../packages/core-py && uv run pytest
```

- [ ] **Step 4: Commit, PR, merge, bulk close**

Same pattern as Task 1.

- [ ] **Step 5: Release**

```bash
gh workflow run CD -f release_type=stable
```

---

## Task 3: wet-mcp (51 PRs, 4 issues)

**Repo:** `C:/Users/n24q02m-wlap/projects/wet-mcp`

**Open Issues:**
- #668 Update mcp-relay-core to 1.2.0
- #667 Update n24q02m-web-core to 1.0.1
- #666 Update qwen3-embed to 1.6.0
- #231 Renovate Dashboard (no action)

**Open PRs (51):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY | #650, #641, #630, #626 (SQL injection in db.py x4), #649, #647 | 6 |
| PERF | #657 (JSON parse), #644 (async I/O), #638 (N+1 sitemap), #617 (N+1 docs), #614 (unused import), #613 (SQLite batch), #611 (SQLite perf) | 7 |
| TEST | #654, #652, #651, #649, #648, #647, #646, #645, #643, #642, #640, #637, #635, #631, #628, #627, #624, #623, #621, #620, #616 | 21 |
| FIX/CLEANUP | #655, #653, #639, #636, #634, #633, #632, #629, #625, #622, #619, #618, #615 | 13 |
| DEPS | #656, #610, #609 | 3 |

**Dependencies to update:**
- `mcp-relay-core` >= 1.2.0 (resolves #668)
- `qwen3-embed` >= latest from Task 1 (resolves #666)
- `n24q02m-web-core` >= 1.0.1 (resolves #667)

- [ ] **Step 1: Review all 51 PRs** (focus on SQL injection #650, #641, #630, #626)
- [ ] **Step 2: Implement on branch + update 3 dependencies**
- [ ] **Step 3: Run tests** — `uv run pytest --tb=short -q`
- [ ] **Step 4: Commit, PR, merge, bulk close 51 PRs + 3 issues (#668, #667, #666)**
- [ ] **Step 5: Release** — `gh workflow run CD -f release_type=stable`

---

## Task 4: mnemo-mcp (37 PRs, 3 issues)

**Repo:** `C:/Users/n24q02m-wlap/projects/mnemo-mcp`

**Open Issues:**
- #320 Update mcp-relay-core to 1.2.0
- #319 Update qwen3-embed to 1.6.0
- #111 Renovate Dashboard (no action)

**Open PRs (37):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY | #309 (SQL injection) | 1 |
| PERF | #299 (N+1 FTS), #296 (N+1 graph), #290 (N+1 upsert INSERT), #289 (N+1 upsert UPDATE), #280 (string concat) | 5 |
| TEST | #306, #302, #295, #286, #301 (fixtures) | 5 |
| CLEANUP | #308, #307, #305, #304, #303, #300, #298, #297, #294, #293, #292, #291, #288, #287, #285, #284, #283, #282, #281, #279 (Broad Exception x20) | 20 |
| DEPS | #310 (docker login) | 1 |

Note: 20 of 37 PRs are "Broad Exception Catching" — most will be REJECTED (intentional catch-all in MCP tool handlers).

- [ ] **Step 1: Review all 37 PRs** (accept SQL injection + N+1 fixes, reject most broad-exception)
- [ ] **Step 2: Implement on branch + update 2 dependencies**
- [ ] **Step 3: Run tests** — `uv run pytest --tb=short -q`
- [ ] **Step 4: Commit, PR, merge, bulk close 37 PRs + 2 issues (#320, #319)**
- [ ] **Step 5: Release** — `gh workflow run CD -f release_type=stable`

---

## Task 5: better-code-review-graph (43 PRs, 3 issues)

**Repo:** `C:/Users/n24q02m-wlap/projects/better-code-review-graph`

**Open Issues:**
- #114 Update mcp-relay-core to 1.2.0
- #113 Update qwen3-embed to 1.6.0
- #2 Renovate Dashboard (no action)

**Open PRs (43):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY | #93, #91, #90 (SQL injection), #70, #66 (input length DoS) | 5 |
| PERF | #103, #96, #95, #86, #74, #71, #69 (N+1, cosine, graph) | 7 |
| TEST | #89, #85, #82, #81, #79, #77, #72 | 7 |
| FIX | #104, #102, #101, #100, #99, #98, #97, #94, #92, #88, #87, #84, #83, #80, #78, #76, #75, #73 (nested blocks, complex fns) | 18 |
| DEPS | #68, #67, #65, #64 | 4 |

Note: fastmcp v3 deps (#68, #67) — REVIEW carefully for breaking changes.

- [ ] **Step 1: Review all 43 PRs**
- [ ] **Step 2: Implement on branch + update 2 dependencies**
- [ ] **Step 3: Run tests** — `uv run pytest --tb=short -q`
- [ ] **Step 4: Commit, PR, merge, bulk close 43 PRs + 2 issues**
- [ ] **Step 5: Release**

---

## Task 6: better-telegram-mcp (34 PRs, 3 issues)

**Repo:** `C:/Users/n24q02m-wlap/projects/better-telegram-mcp`

**Open Issues:**
- #134 Update mcp-relay-core to 1.2.0
- #74 Relay E2E encryption feature (verify if already implemented, then close)
- #14 Renovate Dashboard (no action)

**Open PRs (34):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY | #124 (insecure 0.0.0.0), #123/#121 (rate limit), #117 (hardcoded salt), #104/#103 (TOCTOU) | 6 |
| PERF | #127 (sync file read), #126 (sync file write), #105 (sync chmod) | 3 |
| TEST | #133, #130, #129, #128, #125, #122, #119, #118, #116, #115, #114, #113, #112, #111, #110, #109, #108, #107, #106 | 19 |
| FIX | #132 (CLI typer), #131 (too many params), #120 (long async fn) | 3 |
| DEPS | #102, #101, #100 | 3 |

- [ ] **Step 1: Review all 34 PRs + verify #74 is already implemented**
- [ ] **Step 2: Implement on branch + update mcp-relay-core dep**
- [ ] **Step 3: Run tests** — `uv run pytest --tb=short -q`
- [ ] **Step 4: Commit, PR, merge, bulk close 34 PRs + 2 issues (#134, #74)**
- [ ] **Step 5: Release**

---

## Task 7: better-godot-mcp (28 PRs, 1 issue)

**Repo:** `C:/Users/n24q02m-wlap/projects/better-godot-mcp`

**Open Issues:**
- #53 Renovate Dashboard (no action)

**Open PRs (28):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY | #370 (INI injection), #359 (binary exec), #347 (process kill), #346 (ReDoS) | 4 |
| PERF | #369, #366, #360, #355, #352, #349, #348, #345 (input map, array, string, regex) | 8 |
| TEST | #363, #361, #357, #356, #354 | 5 |
| FIX/CLEANUP | #365, #364, #362, #358, #353, #351, #350 (unused fns, type checks) | 7 |
| DEPS | #368, #367, #344, #343 | 4 |

- [ ] **Step 1: Review all 28 PRs**
- [ ] **Step 2: Implement on branch**
- [ ] **Step 3: Run tests** — `npx vitest run`
- [ ] **Step 4: Commit, PR, merge, bulk close 28 PRs**
- [ ] **Step 5: Release**

---

## Task 8: better-email-mcp (0 PRs, 3 issues)

**Repo:** `C:/Users/n24q02m-wlap/projects/better-email-mcp`

**Open Issues:**
- #300 Update mcp-relay-core to 1.2.0
- #241 Relay setup feature (verify if already implemented)
- #22 Renovate Dashboard (no action)

**No open PRs.** Only issue resolution needed.

- [ ] **Step 1: Verify relay is implemented and mcp-relay-core is >= 1.2.0**

```bash
cd /c/Users/n24q02m-wlap/projects/better-email-mcp
grep "mcp-relay-core" package.json
```

- [ ] **Step 2: Close issues if already resolved**

```bash
unset GITHUB_TOKEN
gh issue close 300 --comment "mcp-relay-core already updated to ^1.2.0 in package.json."
gh issue close 241 --comment "Relay setup implemented via mcp-relay-core integration. See relay-setup.ts and relay-schema.ts."
```

- [ ] **Step 3: Release if needed** (only if there are unreleased changes on main)

---

## Task 9: better-notion-mcp (1 PR, 2 issues)

**Repo:** `C:/Users/n24q02m-wlap/projects/better-notion-mcp`

**Open Issues:**
- #367 Update mcp-relay-core to 1.2.0
- #138 Renovate Dashboard (no action)

**Open PRs:**
- #366 OyaAIProd SafeSkill badge — CLOSE (per user decision)

- [ ] **Step 1: Close OyaAIProd PR and verify deps**

```bash
cd /c/Users/n24q02m-wlap/projects/better-notion-mcp
unset GITHUB_TOKEN
gh pr close 366 --comment "Thank you for the security scan. We use our own security tooling (CodeQL + Semgrep). Closing per project policy."
gh issue close 367 --comment "mcp-relay-core already updated to ^1.2.0."
```

- [ ] **Step 2: Release if needed**

---

## Task 10: claude-plugins (21 PRs, 1 issue)

**Repo:** `C:/Users/n24q02m-wlap/projects/claude-plugins`

**Open Issues:**
- #5 Renovate Dashboard (no action)

**Open PRs (21):**

| Category | PRs | Count |
|----------|-----|-------|
| SECURITY (CRITICAL) | #30, #29, #28, #22, #17, #16, #12 (command injection in CD, code injection, data exfiltration) | 7 |
| SECURITY (MEDIUM) | #13 (unsafe python -c), #10 (SIGPIPE), #20 (sync-plugins) | 3 |
| PERF | #21, #18, #11 (subshell, dir check) | 3 |
| TEST | #26, #19 (edge cases, session-start hook) | 2 |
| FIX | #27, #25, #24, #23 (duplicate logic, inline Python) | 4 |
| OTHER | #15 (no valid optimization), #14 (deps) | 2 |

CRITICAL: 7 security PRs about command injection in CD workflow. These are high priority.

- [ ] **Step 1: Review all 21 PRs** (CRITICAL security first)
- [ ] **Step 2: Implement on branch**
- [ ] **Step 3: Run validation** (no test suite — manual check of scripts/workflows)
- [ ] **Step 4: Commit, PR, merge, bulk close 21 PRs**
- [ ] **Step 5: Push** (no CD release for marketplace repo)

---

## Task 11: n24q02m profile (0 issues, 0 PRs)

**Repo:** `C:/Users/n24q02m-wlap/projects/n24q02m`

- [ ] **Step 1: Verify profile README is current**

```bash
cd /c/Users/n24q02m-wlap/projects/n24q02m
cat README.md
```

Check: links work, descriptions accurate, no stale references.

- [ ] **Step 2: Update if needed**

---

## Task 12: Full Live E2E Testing

**Depends on:** Tasks 1-11 ALL complete.

This task requires real credentials and manual browser interaction. Must be done directly with user (1-1).

- [ ] **Step 1: Prepare credentials**

User provides:
- Telegram BOT_TOKEN
- Telegram phone number (for user mode)
- Email: Gmail app password
- Email: Outlook account (for OAuth DCF)
- Notion: NOTION_TOKEN
- Embedding: JINA_AI_API_KEY or GEMINI_API_KEY (optional)

- [ ] **Step 2: Test each server — relay mode**

For each server (wet, mnemo, crg, telegram-bot, telegram-user, email-gmail, email-outlook, notion):
1. Start server from source WITHOUT env vars
2. Relay URL appears in stderr
3. Open in Chrome, enter credentials
4. Server receives config
5. Run full tool suite via MCP protocol

```bash
# Example: wet-mcp relay mode
cd /c/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
```

- [ ] **Step 3: Test each server — env mode**

```bash
# Python servers
for repo in wet-mcp mnemo-mcp better-code-review-graph better-telegram-mcp; do
  cd /c/Users/n24q02m-wlap/projects/$repo
  uv run pytest tests/test_e2e.py --setup=env -v --tb=short
done

# TypeScript servers
for repo in better-godot-mcp better-email-mcp; do
  cd /c/Users/n24q02m-wlap/projects/$repo
  E2E_SETUP=env npx vitest run tests/e2e.test.ts
done
```

- [ ] **Step 4: Test each server — plugin mode**

```bash
# Python servers
for repo in wet-mcp mnemo-mcp better-code-review-graph better-telegram-mcp; do
  cd /c/Users/n24q02m-wlap/projects/$repo
  uv run pytest tests/test_e2e.py --setup=plugin -v --tb=short
done

# TypeScript servers
for repo in better-godot-mcp better-email-mcp; do
  cd /c/Users/n24q02m-wlap/projects/$repo
  E2E_SETUP=plugin npx vitest run tests/e2e.test.ts
done
```

- [ ] **Step 5: Test HTTP mode (telegram, email, notion)**

```bash
# Telegram HTTP multi-user
cd /c/Users/n24q02m-wlap/projects/better-telegram-mcp
# Start HTTP server, test via API

# Email HTTP
cd /c/Users/n24q02m-wlap/projects/better-email-mcp
E2E_SETUP=http npx vitest run tests/e2e.test.ts

# Notion HTTP OAuth
cd /c/Users/n24q02m-wlap/projects/better-notion-mcp
# Test via production URL: https://better-notion-mcp.n24q02m.com/mcp
```

- [ ] **Step 6: Final marketplace re-sync**

```bash
cd /c/Users/n24q02m-wlap/projects/claude-plugins
bash scripts/sync-plugins.sh
git add -A && git commit -m "feat: sync plugins after consolidated PR resolution"
git push origin main
```

- [ ] **Step 7: Verify plugin install**

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

- [ ] **Step 8: Final verification**

```bash
# Confirm 0 open issues/PRs (except Renovate Dashboard)
for repo in n24q02m/wet-mcp n24q02m/mnemo-mcp n24q02m/better-code-review-graph n24q02m/better-telegram-mcp n24q02m/better-godot-mcp n24q02m/better-email-mcp n24q02m/better-notion-mcp n24q02m/claude-plugins n24q02m/mcp-relay-core n24q02m/qwen3-embed; do
  ISSUES=$(gh issue list -R "$repo" --state open --limit 500 --json number -q '[.[] | select(.title | test("Dependency Dashboard") | not)] | length')
  PRS=$(gh pr list -R "$repo" --state open --limit 500 --json number -q 'length')
  echo "$repo: issues=$ISSUES prs=$PRS"
done
```

Expected: ALL repos show `issues=0 prs=0` (except Renovate Dashboard issues).
