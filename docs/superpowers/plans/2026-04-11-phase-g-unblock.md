# Phase G — Unblock P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec**: `specs/2026-04-10-mcp-core-unified-transport-design.md`
**Roadmap**: `plans/2026-04-10-phase3-roadmap.md` (phase G slice)
**Date**: 2026-04-11 (to be executed 2026-04-11 onward)

**Goal:** Unblock the Phase H/I/J critical path by resolving the 5 P0 issues (telegram conflict, wet-mcp CI, CodeQL noise, Dependabot vulns, notion HTTP template inventory) and capture a credential_state file inventory for Phase J, so later phases can begin from a clean baseline.

**Architecture:** Each task is self-contained — investigate the concrete state, apply a minimal fix, verify via evidence, commit. No cross-task dependencies except G4 (Dependabot) which may be easier to verify after G2 (CI unblocked).

**Changes from v1**:
- G5 removed (Claude Code HTTP schema already verified via backup files + better-notion-mcp production use, no more investigation needed)
- G6 expanded to inventory plugin.json format across all 6 credential repos (notion already HTTP — template for others)
- G7 added: credential_state.py inventory for Phase J deletion list

**Tech Stack:** Python 3.13 + uv + ruff + ty + pytest; Node 20 + pnpm; `gh` CLI for GitHub evidence; `git` for repo ops.

---

## Pre-flight (once, before any task)

- [ ] **Step P.1: Confirm worktree and branch**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
git status
git rev-parse --abbrev-ref HEAD
```

Expected: `On branch feat/phase3-mcp-core-unified`, working tree clean.

- [ ] **Step P.2: Verify `gh` auth works and can read all 12 repos**

```bash
gh api user --jq '.login'
gh api repos/n24q02m/wet-mcp --jq '.name'
gh api repos/n24q02m/better-telegram-mcp --jq '.name'
```

Expected: `n24q02m`, `wet-mcp`, `better-telegram-mcp` — no 401/404 errors.

---

### Task G1: Resolve better-telegram-mcp http_multi_user.py DU state

**Files:**
- Investigate: `C:/Users/n24q02m-wlap/projects/better-telegram-mcp/.git/MERGE_HEAD`
- Investigate: `C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/transports/http_multi_user.py`
- Modify: same file (accept/reject/merge)
- Verify: `pytest` baseline
- Commit: in better-telegram-mcp repo (separate repo, not claude-plugins worktree)

**Context (from audit 2026-04-10):** `git status` shows `DU src/better_telegram_mcp/transports/http_multi_user.py`. `DU` means "deleted by us, updated by them" — an in-progress merge where local side deleted the file but remote updated it. File currently on disk is the "them" version (full 1500+ lines, no conflict markers). Also `Your branch and 'origin/main' have diverged, and have 1 and 8 different commits each` — indicates merge or rebase was started but not finished. 11 other files are in M/A state.

- [ ] **Step 1: Check whether a merge is actually in progress**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
ls -la .git/MERGE_HEAD .git/MERGE_MSG .git/REBASE_HEAD .git/rebase-merge .git/rebase-apply 2>&1
git status --porcelain=v2 --branch 2>&1 | head -30
```

Expected: one of `.git/MERGE_HEAD`, `.git/REBASE_HEAD`, or rebase dirs exists. `status --porcelain=v2` prints `# branch.ab +1 -8` meaning 1 commit ahead, 8 behind. If no merge/rebase state but `DU` shows, the index is in an orphaned conflicted state from a previous aborted operation.

- [ ] **Step 2: Capture both sides of http_multi_user.py for comparison**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
git show :1:src/better_telegram_mcp/transports/http_multi_user.py > /tmp/http_mu_base.py 2>/dev/null && wc -l /tmp/http_mu_base.py || echo "no stage 1 (no common base)"
git show :2:src/better_telegram_mcp/transports/http_multi_user.py > /tmp/http_mu_ours.py 2>/dev/null && wc -l /tmp/http_mu_ours.py || echo "no stage 2 (we deleted)"
git show :3:src/better_telegram_mcp/transports/http_multi_user.py > /tmp/http_mu_theirs.py 2>/dev/null && wc -l /tmp/http_mu_theirs.py || echo "no stage 3 (they deleted)"
wc -l src/better_telegram_mcp/transports/http_multi_user.py
```

Expected: `no stage 2` (because DU = we deleted) + `wc -l` on stage 3 and working tree both ~1500 lines. Working tree file is already the "theirs" version.

- [ ] **Step 3: Decide resolution — keep the theirs version**

**Rationale (locked by spec §2.4):** Phase 3 uses HTTP only for telegram with OAuth 2.1 self-hosted AS. `http_multi_user.py` is load-bearing for the new architecture — we cannot drop it. The "deleted by us" side came from an earlier attempt to revert multi-user refactor. Keep "theirs".

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
git add src/better_telegram_mcp/transports/http_multi_user.py
git status --porcelain=v2 | grep http_multi_user
```

Expected: file moves from `DU` to `M ` (staged modification) or vanishes from status (if already matching HEAD+theirs).

- [ ] **Step 4: Inspect remaining 11 dirty files — verify none reintroduce conflict**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
git diff --cached --stat
git diff --stat
grep -rln "<<<<<<< \|======= \|>>>>>>> " src/ tests/ 2>&1 || echo "no conflict markers"
```

Expected: stat output shows all 12 files (11 previously in M/A + 1 now staged). `grep` prints `no conflict markers`.

- [ ] **Step 5: Run pytest to confirm baseline works**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
uv run pytest -q --tb=short 2>&1 | tail -40
```

Expected: `passed` (some may `skip` for integration). Any failure means the merge introduced a regression — STOP, investigate, do NOT commit.

- [ ] **Step 6: Commit resolution**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
git add -A
git commit -m "fix: resolve http_multi_user.py DU state from aborted merge

Keep theirs version of http_multi_user.py; deleted-by-us side came from
an earlier revert attempt that conflicts with Phase 3 multi-user OAuth
architecture (spec 2026-04-10).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git log --oneline -1
git status
```

Expected: commit hash printed, `working tree clean`. Do NOT push yet — push decision deferred until end of Phase G.

---

### Task G2: Diagnose and fix wet-mcp main branch CI failure

**Files:**
- Investigate: `gh run view` output for latest main-branch failure
- Modify: whichever file is root cause (unknown until investigation)
- Test: `uv run pytest` locally on main branch
- Commit: in wet-mcp repo

**Context (from audit):** `gh run list --branch main` shows 3 consecutive failures on main for workflow `CI` + `Dependabot Updates`. Commit "fix: merge incoming changes" run 24171981938 failed on "Lint & Test (ubuntu-latest)". Root cause not yet identified — step logs start with generic runner setup. Investigation is part of this task.

- [ ] **Step 1: Fetch latest main branch state and capture failing run id**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
git fetch origin main
git log --oneline origin/main | head -5
RUN_ID=$(gh run list --branch main --workflow CI --limit 3 --json databaseId,conclusion --jq '[.[] | select(.conclusion == "failure")] | .[0].databaseId')
echo "RUN_ID=$RUN_ID"
```

Expected: non-empty `RUN_ID` — the most recent failing CI run on main. If `RUN_ID` is empty, main branch CI is actually green already and only G3/G4 remain for wet-mcp.

- [ ] **Step 2: Identify failing job and step**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
gh run view $RUN_ID --json jobs --jq '.jobs[] | {name, conclusion, steps: [.steps[] | select(.conclusion=="failure") | .name]}'
```

Expected: prints job names and specific failed step names. Common failures: `Run ruff check`, `Run ty check`, `Run pytest`, `Install dependencies`.

- [ ] **Step 3: Pull only the failing step's log for the root cause**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
gh run view $RUN_ID --log-failed 2>&1 | grep -E "FAIL|Error|error:|ERROR|✗" | head -40 | tee /tmp/wet-mcp-ci-failure.txt
```

Expected: actual error line(s). Examples of likely findings:
- `FAILED tests/test_sync.py::test_x` → test regression
- `error[type-error]` → ty type error
- `error: Cannot resolve` → import error from Dependabot-upgraded deps
- `Ruff would reformat` → format drift

Record root cause.

- [ ] **Step 4: Reproduce locally on main**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
git checkout main
git pull --ff-only origin main
uv sync --group dev
uv run ruff check . 2>&1 | tail -20
uv run ruff format --check . 2>&1 | tail -20
uv run ty check 2>&1 | tail -20
uv run pytest -q --tb=short 2>&1 | tail -40
```

Expected: at least one of lint/format/type/test fails locally matching CI.

- [ ] **Step 5: Apply minimal fix based on root cause category**

For each category (pick the one that matches Step 3 output):

**5a. Lint/format failures:**
```bash
uv run ruff check --fix .
uv run ruff format .
```

**5b. Type errors** — open the file + line from Step 3 output, apply minimal annotation or cast. Do NOT `type: ignore` unless no reasonable fix exists.

**5c. Test failures** — open the test file, read the assertion, identify whether test or production code is wrong. Fix the one that violates the spec invariant. If the test is asserting on a Phase 3 superseded behavior (e.g. stdio mode), defer to Phase J and mark test `@pytest.mark.skip(reason="Phase 3: stdio removed, see spec 2026-04-10")`.

**5d. Dependency resolution errors** — likely intersecting with G4. Defer: proceed to G4 first, return here after.

- [ ] **Step 6: Re-run full lint+type+test locally**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run pytest -q --tb=short 2>&1 | tail -20
```

Expected: all four commands exit 0, pytest prints `passed` with 0 failures.

- [ ] **Step 7: Commit the fix**

Commit message template — replace the three bracketed placeholders with concrete values from Steps 3, 5, and 6:

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
git add -A
git diff --cached --stat
# Replace: CATEGORY = one of {lint, format, type, test, deps}
# Replace: ROOT_CAUSE = one-line description copied from /tmp/wet-mcp-ci-failure.txt
# Replace: FIX_SUMMARY = one-line description of what was changed to resolve it
CATEGORY="<lint|format|type|test|deps>"
ROOT_CAUSE="<one-line from /tmp/wet-mcp-ci-failure.txt>"
FIX_SUMMARY="<one-line what you changed>"
git commit -m "fix: unblock main branch CI ($CATEGORY)

Root cause: $ROOT_CAUSE
Fix: $FIX_SUMMARY

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git log --oneline -1
```

Expected: commit made. Do NOT push yet. Note: the three variables MUST be set before running `git commit` — bash will substitute them. If the worker runs them as-is with literal `<...>` content, the commit message will still be valid Markdown but will not meaningfully describe the fix.

- [ ] **Step 8: Push to trigger CI, verify green**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
git push origin main
sleep 5
gh run list --branch main --workflow CI --limit 1 --json databaseId,status,conclusion,url
```

Expected: new run `in_progress`. Wait for completion via next step.

- [ ] **Step 9: Wait for CI and capture result**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
gh run watch $(gh run list --branch main --workflow CI --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
```

Expected: exit 0, final status `success`. If failure, return to Step 3 with fresh logs.

---

### Task G3: Dismiss 15 CodeQL false-positive alerts

**Files:**
- GitHub API: `repos/n24q02m/wet-mcp/code-scanning/alerts/<N>` (10 alerts)
- GitHub API: `repos/n24q02m/mnemo-mcp/code-scanning/alerts/<N>` (3 alerts)
- GitHub API: `repos/n24q02m/web-core/code-scanning/alerts/<N>` (2 alerts)
- No file modifications

**Context (from audit 2026-04-10, all 15 alerts enumerated):**

All 15 alerts are `py/incomplete-url-substring-sanitization` in **test files only**, not production code. Examples:

| Repo | Alert # | Path | Line | String being matched |
|------|--------:|------|-----:|----------------------|
| wet-mcp | 98 | tests/test_searxng.py | 152 | `a.com` |
| wet-mcp | 67,66,65,64 | tests/test_docs_coverage.py | 742,701,527,229 | `github.com` |
| wet-mcp | 63 | tests/test_coverage_misc.py | 953 | `https://example.com` |
| wet-mcp | 62,61 | tests/test_real_comprehensive.py | 88,81 | `dry-rb.org` |
| wet-mcp | 60,59 | tests/test_real_comprehensive.py | 74,67 | `inertiajs.com` |
| mnemo-mcp | 3 | tests/test_server_setup_actions.py | 291 | `https://setup.url` |
| mnemo-mcp | 2 | tests/test_sync_security.py | 15 | `apps.googleusercontent.com` |
| mnemo-mcp | 1 | tests/test_config.py | 277 | `apps.googleusercontent.com` |
| web-core | 2 | tests/test_http/test_url.py | 39 | `example.com` |
| web-core | 1 | tests/test_scraper/test_state.py | 34 | `https://example.com` |

**Justification (same for all 15):** Test code uses `substring in url` to assert that a URL contains a domain name. These are **test assertions**, not runtime sanitization — no untrusted input ever reaches them, no security boundary exists. CodeQL pattern `py/incomplete-url-substring-sanitization` targets production code that uses substring matching as a security check. False positive by rule scope.

- [ ] **Step 1: Dismiss wet-mcp alerts 59-67, 98 (10 alerts)**

```bash
for N in 98 67 66 65 64 63 62 61 60 59; do
  gh api -X PATCH repos/n24q02m/wet-mcp/code-scanning/alerts/$N \
    -f state=dismissed \
    -f dismissed_reason=false_positive \
    -f dismissed_comment="Test file assertion using \`substring in url\` — not a runtime sanitization check. Rule py/incomplete-url-substring-sanitization targets production code security boundaries. False positive by rule scope (spec 2026-04-10 Phase G3)."
  sleep 1
done
```

Expected: each PATCH returns JSON with `"state": "dismissed"`.

- [ ] **Step 2: Verify wet-mcp open alerts now 0**

```bash
gh api "repos/n24q02m/wet-mcp/code-scanning/alerts?state=open" --jq 'length'
```

Expected: `0`.

- [ ] **Step 3: Dismiss mnemo-mcp alerts 1, 2, 3**

```bash
for N in 1 2 3; do
  gh api -X PATCH repos/n24q02m/mnemo-mcp/code-scanning/alerts/$N \
    -f state=dismissed \
    -f dismissed_reason=false_positive \
    -f dismissed_comment="Test file assertion using \`substring in url\` — not a runtime sanitization check. Rule py/incomplete-url-substring-sanitization targets production code security boundaries. False positive by rule scope (spec 2026-04-10 Phase G3)."
  sleep 1
done
gh api "repos/n24q02m/mnemo-mcp/code-scanning/alerts?state=open" --jq 'length'
```

Expected: final `length` is `0`.

- [ ] **Step 4: Dismiss web-core alerts 1, 2**

```bash
for N in 1 2; do
  gh api -X PATCH repos/n24q02m/web-core/code-scanning/alerts/$N \
    -f state=dismissed \
    -f dismissed_reason=false_positive \
    -f dismissed_comment="Test file assertion using \`substring in url\` — not a runtime sanitization check. Rule py/incomplete-url-substring-sanitization targets production code security boundaries. False positive by rule scope (spec 2026-04-10 Phase G3)."
  sleep 1
done
gh api "repos/n24q02m/web-core/code-scanning/alerts?state=open" --jq 'length'
```

Expected: final `length` is `0`.

- [ ] **Step 5: Record evidence in claude-plugins worktree**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
mkdir -p docs/superpowers/evidence
cat > docs/superpowers/evidence/2026-04-11-g3-codeql-dismissals.md <<'EOF'
# Phase G3 — CodeQL false-positive dismissals

Date: 2026-04-11
Executed by: Claude Code session
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md`

## Dismissed (15 total)

- wet-mcp #98, 67, 66, 65, 64, 63, 62, 61, 60, 59
- mnemo-mcp #1, 2, 3
- web-core #1, 2

All 15 match rule `py/incomplete-url-substring-sanitization` in test files.

## Justification

Test assertions use `substring in url` to verify that URL responses contain
expected domain names. These are unit test assertions, NOT runtime sanitization.
CodeQL rule targets production code security boundaries where untrusted input
is substring-matched. No untrusted input reaches test code. False positive by
rule scope.

## Verification

```
gh api "repos/n24q02m/wet-mcp/code-scanning/alerts?state=open" --jq 'length' → 0
gh api "repos/n24q02m/mnemo-mcp/code-scanning/alerts?state=open" --jq 'length' → 0
gh api "repos/n24q02m/web-core/code-scanning/alerts?state=open" --jq 'length' → 0
```
EOF
git add docs/superpowers/evidence/2026-04-11-g3-codeql-dismissals.md
git commit -m "feat: record Phase G3 CodeQL dismissal evidence

15 alerts dismissed across wet-mcp, mnemo-mcp, web-core. All false
positives in test files per rule scope analysis.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Expected: commit made in worktree.

---

### Task G4: Fix 2 Dependabot alerts in wet-mcp

**Files:**
- Modify: `wet-mcp/pyproject.toml` (constrain versions)
- Modify: `wet-mcp/uv.lock` (via `uv lock --upgrade-package`)
- Test: `uv run pytest`
- Commit: in wet-mcp repo

**Context (from audit, exact CVE details captured):**

| Alert # | Package | Current vulnerable range | Fixed version | Severity |
|--------:|---------|--------------------------|---------------|----------|
| 15 | `langchain-core` | `< 0.3.84` and `>= 1.0.0a1, < 1.2.28` | `0.3.84` OR `1.2.28` | medium (CVSS 5.3) — CVE-2026-40087 f-string validation |
| 14 | `cryptography` | `>= 45.0.0, < 46.0.7` | `46.0.7` | medium (CVSS 6.9 v4) — CVE-2026-39892 buffer overflow non-contiguous buffer |

- [ ] **Step 1: Check current pinned versions in wet-mcp**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
grep -E "^langchain-core|^cryptography" uv.lock 2>&1 | head -5
grep -E "langchain-core|cryptography" pyproject.toml 2>&1
```

Expected: current versions printed. Note which major line wet-mcp is on for `langchain-core` (0.3.x or 1.x).

- [ ] **Step 2: Upgrade langchain-core to first patched version**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv lock --upgrade-package langchain-core
grep "^langchain-core" uv.lock | head -2
```

Expected: locked version is `0.3.84` or later (if on 0.3.x) OR `1.2.28` or later (if on 1.x).

- [ ] **Step 3: Upgrade cryptography to 46.0.7+**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv lock --upgrade-package cryptography
grep "^cryptography" uv.lock | head -2
```

Expected: locked version is `46.0.7` or later.

- [ ] **Step 4: Verify no transitive dep regressions**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv sync --group dev 2>&1 | tail -10
uv run python -c "import langchain_core; import cryptography; print(langchain_core.__version__, cryptography.__version__)"
```

Expected: both import successfully, versions match Step 2+3.

- [ ] **Step 5: Run full test suite**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest -q --tb=short 2>&1 | tail -40
```

Expected: `passed`. If cryptography bump breaks something in `auth/` or `sync.py` encryption, read the stacktrace and fix the caller (cryptography 46 has a few API renames). Do NOT downgrade.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
git add pyproject.toml uv.lock
git commit -m "fix: patch langchain-core CVE-2026-40087 and cryptography CVE-2026-39892

langchain-core: bump to first patched version (0.3.84 or 1.2.28) to
address incomplete f-string validation in prompt templates.

cryptography: bump to 46.0.7 to address buffer overflow on non-contiguous
buffer input to Hash.update() and similar APIs.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git log --oneline -1
```

Expected: commit made.

- [ ] **Step 7: Push and verify Dependabot alerts auto-close**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
git push origin main
sleep 30
gh api "repos/n24q02m/wet-mcp/dependabot/alerts?state=open" --jq 'length'
```

Expected: length drops to `0` (or stays low if Dependabot hasn't re-scanned yet — retry after 2-5 min).

---

### Task G5: REMOVED

Task G5 (Claude Code HTTP transport schema verification) is removed in plan v2. The schema is already verified via two independent sources:

1. **`~/.claude/backups/.claude.json.backup.*` line 667** — stitch entry uses `"type": "http"`
2. **`better-notion-mcp/.claude-plugin/plugin.json`** — production already uses `"type": "http"` with `https://better-notion-mcp.n24q02m.com/mcp`

No further Phase G investigation needed. Empirical localhost handshake is deferred to Phase M (E2E validation).

---

### Task G6: Inventory plugin.json format across 6 credential repos + verify notion Streamable HTTP spec

**Files:**
- Read: `better-notion-mcp/src/transports/http.ts`
- Read: `better-notion-mcp/package.json` (SDK version)
- Read: `better-notion-mcp/node_modules/@modelcontextprotocol/sdk/package.json`
- Write: `docs/superpowers/evidence/2026-04-11-g6-notion-streamable-http-version.md`
- Commit: in claude-plugins worktree

**Context (from audit):** `grep` found `StreamableHTTPServerTransport` imports in `src/transports/http.ts`. SDK package is `@modelcontextprotocol/sdk`. Need to confirm the SDK version and which MCP protocol version it implements. The 2025-11-25 Streamable HTTP spec is only supported by recent SDK versions.

- [ ] **Step 1: Check package.json for SDK version**

```bash
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp
grep -A 1 '"@modelcontextprotocol/sdk"' package.json
cat node_modules/@modelcontextprotocol/sdk/package.json 2>&1 | grep -E '"name"|"version"' | head -5
```

Expected: pinned version in package.json, installed version in node_modules.

- [ ] **Step 2: Check what MCP protocol versions the SDK declares**

```bash
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp
grep -rn "protocolVersion\|PROTOCOL_VERSION\|2025-11-25\|2025-03-26\|2024-11-05" node_modules/@modelcontextprotocol/sdk/dist/types.d.ts node_modules/@modelcontextprotocol/sdk/dist/types.js 2>&1 | head -20
grep -rn "LATEST_PROTOCOL_VERSION\|SUPPORTED_PROTOCOL_VERSIONS" node_modules/@modelcontextprotocol/sdk/dist/ 2>&1 | head -20
```

Expected: finds `LATEST_PROTOCOL_VERSION = "2025-..."` or similar constant.

- [ ] **Step 3: Inspect the actual http.ts implementation**

```bash
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp
head -50 src/transports/http.ts
grep -n "StreamableHTTPServerTransport\|sessionIdGenerator\|sessionId\|Mcp-Session-Id" src/transports/http.ts | head -20
```

Expected: confirms use of `StreamableHTTPServerTransport` with session management.

- [ ] **Step 4: Check for old SSE endpoint presence (spec 2024-11-05 artifact)**

```bash
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp
grep -rn "SSEServerTransport\|/sse\|sseServer\|'sse'" src/transports/ 2>&1 | head -10
```

Expected: `SSEServerTransport` should NOT be present in the HTTP transport if on spec 2025-11-25 (SSE is merged into Streamable HTTP). If found, that indicates a pre-2025-11-25 implementation still lingering.

- [ ] **Step 5: Capture all evidence into shell variables**

```bash
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp
SDK_PIN=$(grep -A 1 '"@modelcontextprotocol/sdk"' package.json | tr -d '\n' | sed 's/.*"@modelcontextprotocol\/sdk":[[:space:]]*"\([^"]*\)".*/\1/')
SDK_INSTALLED=$(cat node_modules/@modelcontextprotocol/sdk/package.json 2>/dev/null | grep '"version"' | head -1 | sed 's/.*"version":[[:space:]]*"\([^"]*\)".*/\1/')
SDK_PROTOCOL=$(grep -rhoE '"20[0-9]{2}-[0-9]{2}-[0-9]{2}"' node_modules/@modelcontextprotocol/sdk/dist/types.* 2>/dev/null | sort -u | tr '\n' ',' | sed 's/,$//')
SSE_FOUND=$(grep -rln "SSEServerTransport" src/transports/ 2>/dev/null | tr '\n' ' ')
[ -z "$SSE_FOUND" ] && SSE_FOUND="none"
echo "SDK_PIN=$SDK_PIN"
echo "SDK_INSTALLED=$SDK_INSTALLED"
echo "SDK_PROTOCOL=$SDK_PROTOCOL"
echo "SSE_FOUND=$SSE_FOUND"
```

Expected: 4 variables set with actual values. Verify all are non-empty (except `SSE_FOUND` which may legitimately be `none`).

- [ ] **Step 6: Derive verdict programmatically**

```bash
VERDICT="unknown"
if echo "$SDK_PROTOCOL" | grep -q "2025-11-25" && [ "$SSE_FOUND" = "none" ]; then
  VERDICT="compliant"
elif echo "$SDK_PROTOCOL" | grep -qE "2025-[0-9]{2}-[0-9]{2}" && [ "$SSE_FOUND" = "none" ]; then
  VERDICT="partial-newer-sdk-needed"
elif [ "$SSE_FOUND" != "none" ]; then
  VERDICT="non-compliant-legacy-sse-present"
else
  VERDICT="non-compliant-old-sdk"
fi
echo "VERDICT=$VERDICT"
```

Expected: one of `compliant`, `partial-newer-sdk-needed`, `non-compliant-legacy-sse-present`, `non-compliant-old-sdk`.

- [ ] **Step 7: Write evidence file with actual captured values**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cat > docs/superpowers/evidence/2026-04-11-g6-notion-streamable-http-version.md <<EOF
# Phase G6 — better-notion-mcp Streamable HTTP spec version

Date: 2026-04-11
Executed by: Claude Code session
Spec: \`specs/2026-04-10-mcp-core-unified-transport-design.md\`

## Evidence collected

### SDK version

- package.json pin: \`$SDK_PIN\`
- installed version: \`$SDK_INSTALLED\`

### Protocol version(s) declared by SDK

- Protocol versions found in SDK types: \`$SDK_PROTOCOL\`

### Implementation file

- \`src/transports/http.ts\` uses \`StreamableHTTPServerTransport\` (verified via grep in Step 3)

### Legacy SSE presence

- \`SSEServerTransport\` in \`src/transports/\`: \`$SSE_FOUND\`

## Verdict

**$VERDICT**

Mapping:

- **compliant**: SDK implements 2025-11-25, no legacy SSE. No transport rewrite in Phase J for notion; only auth middleware swap.
- **partial-newer-sdk-needed**: Uses \`StreamableHTTPServerTransport\` but SDK implements an older spec version. Phase J needs SDK upgrade + re-test as first step.
- **non-compliant-legacy-sse-present**: Legacy \`SSEServerTransport\` still wired up. Phase J needs to remove SSE endpoint.
- **non-compliant-old-sdk**: SDK too old to support any 2025-xx spec. Phase J needs full SDK upgrade + rewrite.

## Next action for Phase J planning

Depends on verdict value above. Record it in the Phase J plan header as blocker / non-blocker.
EOF
cat docs/superpowers/evidence/2026-04-11-g6-notion-streamable-http-version.md | head -30
```

Expected: file written with actual shell variable values substituted (no `$SDK_PIN` literal text).

- [ ] **Step 8: Inventory all 6 credential repos' plugin.json format**

```bash
cd C:/Users/n24q02m-wlap/projects
for repo in wet-mcp mnemo-mcp better-code-review-graph better-telegram-mcp better-email-mcp better-notion-mcp; do
  echo "=== $repo ==="
  cat $repo/.claude-plugin/plugin.json | python -c "import sys, json; d=json.load(sys.stdin); srv=next(iter(d.get('mcpServers', {}).values())); print('type:', srv.get('type', 'stdio (command-based)')); print('url:', srv.get('url', 'n/a')); print('command:', srv.get('command', 'n/a'))"
done
```

Expected:
- notion: `type: http, url: https://better-notion-mcp.n24q02m.com/mcp`
- 5 others: `type: stdio, command: uvx|npx`

- [ ] **Step 9: Append inventory to evidence file**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cat >> docs/superpowers/evidence/2026-04-11-g6-notion-streamable-http-version.md <<'EOF'

## plugin.json format inventory (all 6 credential repos)

| Repo | Transport type | URL or command | Phase J action |
|------|---------------|----------------|----------------|
| better-notion-mcp | **http** (production) | https://better-notion-mcp.n24q02m.com/mcp | Reference template |
| wet-mcp | stdio | `uvx --python 3.13 wet-mcp` | Flip to `type: http`, local port 41601 |
| mnemo-mcp | stdio | `uvx --python 3.13 mnemo-mcp` | Flip to `type: http`, local port 41602 |
| better-code-review-graph | stdio | `uvx better-code-review-graph` | Flip to `type: http`, local port 41603 |
| better-telegram-mcp | stdio | `uvx --python 3.13 better-telegram-mcp` | Flip to `type: http`, remote URL (Tier B) |
| better-email-mcp | stdio | `npx -y @n24q02m/better-email-mcp` | Flip to `type: http`, remote URL (Tier B) |

notion is the template. Phase J per-repo migration duplicates this format with appropriate URL/port.
EOF
```

- [ ] **Step 10: Commit evidence**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
git add docs/superpowers/evidence/2026-04-11-g6-notion-streamable-http-version.md
git commit -m "feat: record Phase G6 notion spec + 6-repo plugin.json inventory

SDK version, protocol constants, SSE presence captured. Plugin.json
inventory shows notion is the only repo on HTTP transport — others
use stdio and will be migrated in Phase J using notion as template.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Expected: commit made.

---

### Task G7: credential_state inventory for Phase J deletion list

**Files:**
- Read only — no code change
- Write: `docs/superpowers/evidence/2026-04-11-g7-credential-state-inventory.md`
- Commit: in claude-plugins worktree

**Context**: Spec v3 §2.7(b) mandates deletion of `credential_state.py`/`.ts` + inline `AWAITING_SETUP` gates in 6 repos. Phase J will execute deletion. This task captures exact file paths + line ranges so Phase J plan has concrete target list.

- [ ] **Step 1: Enumerate credential_state files**

```bash
cd C:/Users/n24q02m-wlap/projects
for repo in wet-mcp mnemo-mcp better-code-review-graph better-telegram-mcp better-email-mcp better-notion-mcp; do
  echo "=== $repo ==="
  find $repo -type f \( -name "credential_state.py" -o -name "credential-state.ts" -o -name "test_credential_state.py" -o -name "credential-state.test.ts" \) -not -path "*/.venv*" -not -path "*/node_modules/*" -not -path "*/build/*" 2>/dev/null
done
```

Expected: ~12 files listed (1 impl + 1 test per repo).

- [ ] **Step 2: Locate AWAITING_SETUP usage sites in server.py**

```bash
cd C:/Users/n24q02m-wlap/projects
for repo in wet-mcp mnemo-mcp better-code-review-graph better-telegram-mcp; do
  echo "=== $repo server.py AWAITING_SETUP sites ==="
  grep -n "AWAITING_SETUP\|credential_state\|awaiting_setup" $repo/src/*/server.py 2>/dev/null | head -20
done
for repo in better-email-mcp better-notion-mcp; do
  echo "=== $repo init/tools AWAITING_SETUP sites ==="
  grep -rn "AWAITING_SETUP\|credential[- ]state" $repo/src/*.ts $repo/src/tools/ 2>/dev/null | head -20
done
```

Expected: concrete line numbers for each usage site. wet-mcp will show many (seen: lines 58-70, 146, 251-333, 1278-1395).

- [ ] **Step 3: Write inventory evidence file**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cat > docs/superpowers/evidence/2026-04-11-g7-credential-state-inventory.md <<'EOF'
# Phase G7 — credential_state inventory for Phase J deletion list

Date: 2026-04-11
Executed by: Claude Code session
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md` §2.7(b)

## Files to delete in Phase J

Paste output of Step 1 command here — full file path per repo.

## AWAITING_SETUP inline gate sites in server.py / init

Paste output of Step 2 command here — `file.py:line_number` per usage site.

## Replacement plan

Per spec v3 §2.2 and §2.7(b):
- Delete credential_state.py + test_credential_state.py in all 6 repos
- Remove AWAITING_SETUP blocks in server.py / init-server.ts
- Install `mcp_core.auth.middleware` transport-level middleware
- Add `Depends(get_session_creds)` to tool handlers in FastMCP
- Tool code assumes credentials present at runtime

## Verification after Phase J

```bash
# Should return 0 results
grep -rln "AWAITING_SETUP\|credential_state" wet-mcp/src mnemo-mcp/src better-code-review-graph/src better-telegram-mcp/src
grep -rln "AWAITING_SETUP\|credential-state" better-email-mcp/src better-notion-mcp/src
```
EOF
# Manually append Step 1 + Step 2 actual output to the placeholder sections above
```

- [ ] **Step 4: Fill placeholder sections with actual command output**

Re-run Step 1 and Step 2 commands, capture output, and append to the evidence file (replace the "Paste output of Step N command here" lines). Example:

```bash
cd C:/Users/n24q02m-wlap/projects
# Run Step 1 and Step 2, pipe output into the file
for repo in wet-mcp mnemo-mcp better-code-review-graph better-telegram-mcp better-email-mcp better-notion-mcp; do
  echo "=== $repo ==="
  find $repo -type f \( -name "credential_state.py" -o -name "credential-state.ts" -o -name "test_credential_state.py" -o -name "credential-state.test.ts" \) -not -path "*/.venv*" -not -path "*/node_modules/*" -not -path "*/build/*" 2>/dev/null
done >> C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core/docs/superpowers/evidence/2026-04-11-g7-credential-state-inventory.md
```

- [ ] **Step 5: Commit evidence**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
git add docs/superpowers/evidence/2026-04-11-g7-credential-state-inventory.md
git commit -m "feat: record Phase G7 credential_state inventory for Phase J

Captures exact file paths + AWAITING_SETUP usage sites across 6
credential repos. Target list for Phase J deletion per spec v3 §2.7(b).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Expected: commit made.

---

## Phase G Exit Gate

Before starting Phase H, ALL of the following must hold (verify with evidence):

- [ ] **Gate 1: Telegram conflict resolved**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
git status --porcelain | grep -v "^??" | wc -l
```
Expected: `0`.

- [ ] **Gate 2: wet-mcp main branch CI green**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
gh run list --branch main --workflow CI --limit 1 --json conclusion --jq '.[0].conclusion'
```
Expected: `success`.

- [ ] **Gate 3: CodeQL open alerts = 0 for wet-mcp, mnemo-mcp, web-core**

```bash
for REPO in wet-mcp mnemo-mcp web-core; do
  N=$(gh api "repos/n24q02m/$REPO/code-scanning/alerts?state=open" --jq 'length')
  echo "$REPO: $N"
done
```
Expected: all three print `0`.

- [ ] **Gate 4: Dependabot open alerts = 0 for wet-mcp**

```bash
gh api "repos/n24q02m/wet-mcp/dependabot/alerts?state=open" --jq 'length'
```
Expected: `0`.

- [ ] **Gate 5 + 6 + 7: Evidence files committed in worktree**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
ls docs/superpowers/evidence/2026-04-11-g*.md
git log --oneline -10
```
Expected: 3 evidence files present (G3, G6, G7 — G5 removed), commits in git log.

- [ ] **Gate 7: Worktree tests still pass (regression check)**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
bash scripts/sync-plugins.sh --dry-run 2>&1 | tail -5
pytest tests/ -q 2>&1 | tail -5 || echo "no claude-plugins pytest"
```
Expected: no regression from Phase G work.

---

## Post-Phase G actions

After all gates pass:

1. Tag this point in the worktree: `git tag phase-g-complete`
2. Write Phase H plan (`2026-04-??-phase-h-gdrive-appdata.md`) per `writing-plans` skill
3. Present Phase G evidence report to user for sign-off before starting Phase H

## Notes on granularity

- Tasks G1, G2, G4 modify source repos (better-telegram-mcp, wet-mcp). Commits happen in those repos, not in the claude-plugins worktree.
- Tasks G3, G5, G6 write evidence files in the claude-plugins worktree only; no source repo changes.
- Pushing source repo commits: defer push-to-remote decision to Gate verification — all 4 source commits push together at end of Phase G.
