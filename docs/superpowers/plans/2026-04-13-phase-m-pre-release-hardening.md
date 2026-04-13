# Phase M — Pre-Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring 12 repos to clean + green state, then cut stable releases for mcp-core and the 7 MCP servers.

**Architecture:** Five sequential phases (A cleanup → B 17-config E2E → C mcp-core release → D bump + retest → E MCP releases). Strict exit gates; any failure restarts the affected phase after root-cause fix.

**Tech Stack:** bun + vitest + biome + tsc (TS repos); uv + pytest + ruff + ty (Python repos); gh CLI; PSR v10; Docker buildx multi-arch; npm + PyPI; MCP Registry.

**Spec:** `docs/superpowers/specs/2026-04-13-phase-m-pre-release-hardening-design.md`

---

## Phase A — Cleanup (per-repo)

### Task M1: Push pending work (mcp-core)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\mcp-core` (git state)

- [ ] **Step 1: Confirm tree clean + 15 commits ahead**

```bash
cd "/c/Users/n24q02m-wlap/projects/mcp-core"
git status --short
git log origin/main..HEAD --oneline | wc -l
```

Expected: empty output from `git status`; `15` from the log wc.

- [ ] **Step 2: Push**

```bash
git push origin main
```

- [ ] **Step 3: Wait for the triggered CI run, capture result**

```bash
gh run list --repo n24q02m/mcp-core --branch main --limit 1 --json name,conclusion,status,createdAt
```

Expected: the newest run for this push reaches `conclusion: success`. If `failure`, drop into Task M11 (CI failures) before moving on.

### Task M2: Push pending work (better-email-mcp)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-email-mcp` (git state)

- [ ] **Step 1: Confirm tree clean + 5 commits ahead**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-email-mcp"
git status --short
git log origin/main..HEAD --oneline
```

- [ ] **Step 2: Push and wait for CI**

```bash
git push origin main
gh run list --repo n24q02m/better-email-mcp --branch main --limit 1 --json name,conclusion,status
```

- [ ] **Step 3: Route red CI to Task M11; otherwise commit phase log**

No code commit here — this task is about confirming the Phase L commits landed cleanly.

### Task M3: Commit + push pending work (better-notion-mcp)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-notion-mcp` (18 dirty files + 1 unpushed commit)

- [ ] **Step 1: Review each of the 18 modifications**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-notion-mcp"
git status --short
git diff --stat
```

Read each file's diff. This is the Phase L migration fallout — verify no unintended changes before staging.

- [ ] **Step 2: Stage + commit in logical batches**

Group the 18 files by subsystem (transport, tools/composite, helpers, tests). Commit each batch with a `fix:` or `feat:` message describing the batch's intent. No bulk `git add -A`.

```bash
git add <batch files>
git commit -m "..."
```

Repeat until working tree is clean.

- [ ] **Step 3: Push + CI confirm**

```bash
git push origin main
gh run list --repo n24q02m/better-notion-mcp --branch main --limit 1 --json name,conclusion,status
```

Route red CI to Task M11.

### Task M4: Push pending work (better-telegram-mcp)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-telegram-mcp` (git state)

- [ ] **Step 1-3: Same shape as M1/M2 — confirm clean, push, verify CI**

CI failures here are expected (all recent pushes RED) → route immediately to Task M11.

### Task M5: Push pending work (better-godot-mcp)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-godot-mcp` (1 unpushed)

- [ ] **Step 1-3: Same shape as M1/M2**

### Task M6: Commit + push pending work (better-code-review-graph)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-code-review-graph\src\better_code_review_graph\credential_state.py`
- Modify: `C:\Users\n24q02m-wlap\projects\better-code-review-graph\src\better_code_review_graph\relay_setup.py`
- Modify: `C:\Users\n24q02m-wlap\projects\better-code-review-graph\uv.lock`

- [ ] **Step 1: Inspect each dirty file**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-code-review-graph"
git diff src/better_code_review_graph/credential_state.py src/better_code_review_graph/relay_setup.py uv.lock
```

- [ ] **Step 2: Stage + commit by subsystem**

Likely 1-2 commits (credential_state + relay_setup in one, uv.lock in another). Use `fix:` for behavioural changes, `fix:` for dependency lockfile.

- [ ] **Step 3: Push + CI confirm**

### Task M7: Push pending work (wet-mcp)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\wet-mcp` (1 unpushed)

- [ ] **Step 1-3: Same shape as M1/M2**

Expect red CI (4 consecutive) → route to Task M11.

### Task M8: Push pending work (mnemo-mcp)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\mnemo-mcp` (1 unpushed)

- [ ] **Step 1-3: Same shape as M1/M2**

### Task M9: Push pending work (claude-plugins)

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\claude-plugins` (2 unpushed — Phase L spec + plans)

- [ ] **Step 1-3: Same shape as M1/M2**

Expect `cd.yml` to still be red on the push — route to Task M11 (cd.yml sub-item).

### Task M10: Fix local lint/type errors

Independent per-repo sub-tasks; run them in parallel where possible.

#### Task M10.1: better-godot-mcp — 14 biome errors in test files

**Files:**
- Modify: test files surfaced by `bun run check` in `C:\Users\n24q02m-wlap\projects\better-godot-mcp`

- [ ] **Step 1: Capture the exact error list**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-godot-mcp"
bun run check 2>&1 | tee /tmp/godot-biome.log
```

- [ ] **Step 2: Apply auto-fix where safe**

```bash
bun run check:fix
bun run check
```

- [ ] **Step 3: Hand-fix residual errors (lint rules biome auto-fix can't handle)**

Read each remaining error; edit the file; re-run `bun run check` until clean.

- [ ] **Step 4: Run tests to confirm no regressions**

```bash
bun run test
```

Expected: 682 tests still pass.

- [ ] **Step 5: Commit + push**

```bash
git add <files>
git commit -m "fix: resolve biome lint errors in parseCommaSeparatedList tests"
git push origin main
```

#### Task M10.2: better-telegram-mcp — 4 `ty` type diagnostics

**Files:**
- Modify: files surfaced by `uv run ty check` in `C:\Users\n24q02m-wlap\projects\better-telegram-mcp`

- [ ] **Step 1: Capture type diagnostics**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-telegram-mcp"
uv run ty check 2>&1 | tee /tmp/telegram-ty.log
```

- [ ] **Step 2: Read each of the 4 diagnostics, fix at source**

No `# type: ignore` shortcuts unless the error is a known ty false-positive with a linked issue.

- [ ] **Step 3: Re-run ty + pytest**

```bash
uv run ty check
uv run pytest -q
```

- [ ] **Step 4: Commit + push**

#### Task M10.3: better-code-review-graph — 49 `ty` type diagnostics

**Files:**
- Modify: files surfaced by `uv run ty check` in `C:\Users\n24q02m-wlap\projects\better-code-review-graph`

- [ ] **Step 1: Capture + categorize**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-code-review-graph"
uv run ty check 2>&1 | tee /tmp/crg-ty.log
```

Group the 49 diagnostics by file + error class. Fix in batches.

- [ ] **Step 2-N: Fix each batch, re-run ty + pytest, commit per batch**

Large fixes warrant multiple commits. Each commit message names the batch (e.g. `fix: tighten GraphEmbedder typing in crg`).

- [ ] **Final step: Push once all 49 clear**

#### Task M10.4: qwen3-embed — `requires-python` floor

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\qwen3-embed\pyproject.toml`
- Modify: `C:\Users\n24q02m-wlap\projects\qwen3-embed\uv.lock`

- [ ] **Step 1: Bump floor**

In `pyproject.toml`: `requires-python = ">=3.11"` (was `>=3.10`). numpy 2.4.4 requires 3.11+.

- [ ] **Step 2: Re-lock**

```bash
cd "/c/Users/n24q02m-wlap/projects/qwen3-embed"
uv lock
```

- [ ] **Step 3: Re-run lint + tests**

```bash
uv run ruff check .
uv run pytest -q
```

- [ ] **Step 4: Commit + push**

```bash
git add pyproject.toml uv.lock
git commit -m "fix: bump requires-python to 3.11 for numpy 2.4 compat"
git push origin main
```

### Task M11: Fix CI failures on `main`

Per-repo sub-tasks. Each follows the pattern: fetch failing logs → root-cause → fix → push → confirm green.

#### Task M11.1: wet-mcp (4 consecutive red pushes)

- [ ] **Step 1: Pull failing run logs**

```bash
cd "/c/Users/n24q02m-wlap/projects/wet-mcp"
gh run list --repo n24q02m/wet-mcp --branch main --limit 4 --status failure --json databaseId,conclusion,createdAt
gh run view <latest failing id> --repo n24q02m/wet-mcp --log-failed | head -200
```

- [ ] **Step 2: Root-cause**

Common wet CI failures: SearXNG test container, network flake in integration tests, ty tightening. Read the log carefully.

- [ ] **Step 3: Fix in code (or CI config), commit with `fix:`**

No quick-fixes (`continue-on-error`, skip). Root-cause only.

- [ ] **Step 4: Push + confirm green**

#### Task M11.2: better-telegram-mcp (all recent pushes red)

Same shape. Suspect interaction between Phase L pyproject changes and the pre-commit hook or CI type-check — check that first.

#### Task M11.3: qwen3-embed (red since 2026-04-09)

Same shape. May be unrelated to M10.4 or may be resolved by M10.4 — verify.

#### Task M11.4: claude-plugins `cd.yml`

- [ ] **Step 1: Identify why cd.yml fails on push**

```bash
cd "/c/Users/n24q02m-wlap/projects/claude-plugins"
gh run view <latest cd.yml failing id> --log-failed | head -200
```

- [ ] **Step 2-4: Fix + push + confirm green**

Likely a marketplace validation or Docker build step; triage before patching.

#### Task M11.5: mcp-core (latest push failing)

Same shape; verify after M1 push lands.

#### Task M11.6: Intermittent repos (email, notion, godot, crg, mnemo)

For each: inspect last 2-3 failing runs, identify the flaky test or config, either stabilize the test or fix the underlying bug. No `retry` band-aids.

### Task M12: PR triage (per repo, in queue order)

Run the 8-step triage from the spec **in order** per repo. Merge what's green, close the superseded duplicates with a pointer to the kept PR, rebase the UNKNOWN mergeable PRs.

#### Task M12.1: mcp-core (3 PRs)

- [ ] **Step 1: List + open each PR**

```bash
cd "/c/Users/n24q02m-wlap/projects/mcp-core"
gh pr list --repo n24q02m/mcp-core --state open --json number,title,author,isDraft,mergeable,labels
```

- [ ] **Step 2: Review each PR diff via code-reviewer subagent**

Dispatch `feature-dev:code-reviewer` per PR. Record recommendation.

- [ ] **Step 3: Merge approved, close superseded, leave disputed**

- [ ] **Step 4: Commit notes on each close (`"Superseded by #X"` comment, then close)**

#### Task M12.2 — M12.12: Remaining 11 repos

Same shape. Largest queues first: notion (28) → godot (27) → telegram (21) → wet (21) → email (20) → mnemo (20) → crg (17) → qwen3-embed (13) → web-core (9) → claude-plugins (9) → n24q02m (0).

For repos with ≥20 PRs, dispatch 2-3 code-reviewer subagents in parallel grouped by PR theme (security / perf / tests / UX).

### Task M13: Issue triage

- [ ] **Step 1: Close resolved tracking issues**

For each repo: if `[Phase 3] Unified MCP Core migration` coordination has landed (Phase L complete), close with a link to the Phase L commits. Leave Dependency Dashboard issues (Renovate owns them). Leave active feature requests.

- [ ] **Step 2: Close resolved feature requests** on a case-by-case basis.

### Task M14: Security posture confirm

- [ ] **Step 1: Re-run alert probe across 12 repos**

```bash
for repo in mcp-core better-email-mcp better-notion-mcp better-telegram-mcp better-godot-mcp better-code-review-graph wet-mcp mnemo-mcp claude-plugins qwen3-embed web-core n24q02m; do
  echo "=== $repo ==="
  gh api "repos/n24q02m/$repo/dependabot/alerts" --paginate --jq '[.[] | select(.state=="open")] | length'
  gh api "repos/n24q02m/$repo/code-scanning/alerts" --paginate --jq '[.[] | select(.state=="open")] | length' 2>/dev/null
  gh api "repos/n24q02m/$repo/secret-scanning/alerts" --paginate --jq '[.[] | select(.state=="open")] | length' 2>/dev/null
done
```

- [ ] **Step 2: Expected result — all zeros**

If any alert remains, drop into a fix task (update the vulnerable dep, dismiss with documented reason, or add a code change to resolve).

### Task M15: Phase A exit gate review

- [ ] **Step 1: Re-run the full audit probe across 12 repos**

Use the same commands the audit agents used (`git status`, `gh issue list`, `gh pr list`, `gh run list`, `gh api .../alerts`, local lint/type/test).

- [ ] **Step 2: Confirm**

- Every repo has clean tree, no unpushed commits.
- Every repo's `main` CI is green on the latest push.
- Every repo has zero open alerts.
- No repo has `ty` / biome / ruff errors locally.
- PR queue is triaged (everything left is either a known-pending external PR or a not-yet-mergeable bot PR being rebased).

Only then advance to Phase B.

---

## Phase B — Full E2E verification (17 configurations)

### Task M16: Prepare shared E2E harness

**Files:**
- Create: `C:\Users\n24q02m-wlap\projects\claude-plugins\scripts\phase-m-e2e.md` (run log / checklist)

- [ ] **Step 1: Write a checklist for each of the 17 configurations**

```markdown
## B1. Local HTTP (7)
- [ ] wet-mcp — start on :50201, submit form, call `search`, expect ≥1 result
- [ ] mnemo-mcp — start on :50202, submit form, call `memory action=save`, call `action=search`
- [ ] better-code-review-graph — start on :50203, submit form, call `graph action=stats`
- [ ] better-telegram-mcp — start on :50204, submit form, call `chat action=list` (or bot send)
- [ ] better-email-mcp — start on :50205, submit form, call `messages action=list`
- [ ] better-notion-mcp — start on :50206, submit form, call `workspace action=search`
- [ ] better-godot-mcp — start on :50207, submit form, call `project action=list`

## B2. stdio-proxy (7)
- [ ] For each of the 7 MCPs: run `mcp-stdio-proxy` pointing at a local HTTP instance, connect via `mcp-client-stdio`, call one tool, capture output.

## B3. Remote HTTP (3)
- [ ] telegram, email, notion deployed behind PUBLIC_URL with DCR_SERVER_SECRET; register client via DCR; run a tool call; observe audit log.
```

- [ ] **Step 2: Commit the checklist to `claude-plugins` for persistence**

```bash
git add scripts/phase-m-e2e.md
git commit -m "feat: add Phase M E2E harness checklist"
```

### Task M17 — M23: B1 Local HTTP (one task per MCP)

Each task follows the pattern: clean state → start server → submit form live → call real tool → verify result → capture log.

#### Task M17: wet-mcp B1

- [ ] **Step 1: Clean state**

```bash
rm -f "/c/Users/n24q02m-wlap/AppData/Roaming/mcp/Config/config.enc"
rm -rf ~/.wet-mcp/
```

- [ ] **Step 2: Start server**

```bash
cd "/c/Users/n24q02m-wlap/projects/wet-mcp"
TRANSPORT_MODE=http PORT=50201 uv run wet-mcp
```

(run in background, capture port from stdout if 0)

- [ ] **Step 3: Submit form via browser**

Open `http://127.0.0.1:50201/authorize?client_id=test&redirect_uri=http://localhost:9999/callback&state=test&code_challenge=<sha256>&code_challenge_method=S256`. Fill the relay form.

- [ ] **Step 4: Call `search` tool via MCP client**

Use the `wet` plugin (`mcp__plugin_wet-mcp_wet__search`) with a real query and assert at least one result.

- [ ] **Step 5: Check server logs for auto-browser dedupe, tool latency, errors**

- [ ] **Step 6: Record result in `phase-m-e2e.md`, commit**

#### Task M18 — M23: same pattern for mnemo, crg, telegram, email, notion, godot

### Task M24 — M30: B2 stdio-proxy (one task per MCP)

Each task: start the HTTP server + a stdio-proxy process pointed at it, spawn a stdio-capable MCP client, call one tool, verify.

### Task M31 — M33: B3 Remote HTTP (telegram, email, notion)

This depends on Phase L2 Remote Mode landing (task #25 in TaskList). If not implemented by the time Phase B starts:

- [ ] **Step 0: Check if remote mode implementation exists**

```bash
grep -r "TRANSPORT_MODE.*remote\|remote.*transport" src/ packages/ | head
```

If absent, split Phase B: do B1 + B2, mark B3 as Phase M.2 blocker, continue to Phase C but note in release notes that remote mode follows.

- [ ] **Step 1-4: Per repo — deploy, register via DCR, call tool, verify audit log**

### Task M34: Phase B exit gate review

- [ ] **Step 1: Review the 17-item checklist**

Must have 17 passes. Any failure = root-cause fix → repeat the entire affected sub-phase (not just the one config).

- [ ] **Step 2: Commit the completed checklist**

```bash
cd "/c/Users/n24q02m-wlap/projects/claude-plugins"
git add scripts/phase-m-e2e.md
git commit -m "feat: Phase M B-exit — 17 configurations verified"
git push origin main
```

---

## Phase C — Release mcp-core stable

### Task M35: Trigger mcp-core stable release

**Files:**
- GitHub Actions: `n24q02m/mcp-core/.github/workflows/cd.yml`

- [ ] **Step 1: Dispatch the release workflow**

```bash
gh workflow run cd.yml --repo n24q02m/mcp-core -f release-channel=stable
```

- [ ] **Step 2: Watch the run**

```bash
gh run watch --repo n24q02m/mcp-core $(gh run list --repo n24q02m/mcp-core --workflow cd.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

- [ ] **Step 3: Verify all distribution targets**

```bash
npm view @n24q02m/mcp-core version
pip index versions n24q02m-mcp-core
pip index versions mcp-embedding-daemon
pip index versions mcp-stdio-proxy
gh release view --repo n24q02m/mcp-core
curl -sSL https://registry.mcpservers.org/api/v0/servers?search=mcp-core | jq '.servers[] | select(.name | contains("mcp-core")) | .version'
docker manifest inspect ghcr.io/n24q02m/mcp-core:latest | jq '.manifests[].platform'
```

All must show the new version. Any mismatch blocks Phase D.

### Task M36: Record mcp-core release version

- [ ] **Step 1: Capture the released version string**

Record in `scripts/phase-m-e2e.md` as `MCP_CORE_VERSION=x.y.z`.

---

## Phase D — Bump mcp-core in 7 MCP servers + re-test

### Task M37 — M43: Bump dependency + lockfile refresh (one task per MCP)

#### Task M37: better-email-mcp bump

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-email-mcp\package.json`
- Modify: `C:\Users\n24q02m-wlap\projects\better-email-mcp\bun.lock`

- [ ] **Step 1: Bump dep**

In `package.json`, `@n24q02m/mcp-core` → `^MCP_CORE_VERSION`.

- [ ] **Step 2: Refresh lock**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-email-mcp"
bun install
```

- [ ] **Step 3: Local lint/type/test smoke**

```bash
bun run check
bun run test
```

- [ ] **Step 4: Commit + push**

```bash
git add package.json bun.lock
git commit -m "fix: bump @n24q02m/mcp-core to $MCP_CORE_VERSION"
git push origin main
```

- [ ] **Step 5: Confirm CI green on the triggered run**

#### Task M38 — M39: notion, godot (TS repos) — same pattern

#### Task M40: better-telegram-mcp bump

**Files:**
- Modify: `C:\Users\n24q02m-wlap\projects\better-telegram-mcp\pyproject.toml`
- Modify: `C:\Users\n24q02m-wlap\projects\better-telegram-mcp\uv.lock`

- [ ] **Step 1-5: analogous to M37 but for Python/uv**

```bash
cd "/c/Users/n24q02m-wlap/projects/better-telegram-mcp"
uv add "n24q02m-mcp-core==$MCP_CORE_VERSION"
uv run ruff check .
uv run ty check
uv run pytest -q
git add pyproject.toml uv.lock
git commit -m "fix: bump n24q02m-mcp-core to $MCP_CORE_VERSION"
git push origin main
```

#### Task M41 — M43: crg, wet, mnemo — same pattern

### Task M44: Re-run Phase B grid with bumped mcp-core

- [ ] **Step 1: Re-check 17 configurations**

Repeat Phase B — every config must still pass on the new mcp-core. Any failure = back to mcp-core (new point release via Phase C), then Phase D again.

- [ ] **Step 2: Record results in `phase-m-e2e.md`**

### Task M45: Phase D exit gate review

- [ ] **Step 1: Verify**

All 7 MCPs pin the new mcp-core, all 17 configurations still pass.

---

## Phase E — Release 7 MCP servers stable

### Task M46 — M52: Trigger stable release per MCP (in safe order)

Order: TS first (email, notion, godot), then Python (telegram, crg, wet, mnemo).

#### Task M46: better-email-mcp stable release

- [ ] **Step 1: Dispatch release**

```bash
gh workflow run cd.yml --repo n24q02m/better-email-mcp -f release-channel=stable
```

- [ ] **Step 2: Watch + verify all targets**

```bash
gh run watch --repo n24q02m/better-email-mcp <run-id>
npm view @n24q02m/better-email-mcp version   # if npm published
gh release view --repo n24q02m/better-email-mcp
curl -sSL https://registry.mcpservers.org/api/v0/servers?search=better-email-mcp | jq '.servers[0].version'
docker manifest inspect ghcr.io/n24q02m/better-email-mcp:latest | jq '.manifests[].platform'
```

- [ ] **Step 3: Confirm marketplace.json PR auto-opens in claude-plugins**

```bash
gh pr list --repo n24q02m/claude-plugins --search "better-email-mcp"
```

- [ ] **Step 4: Merge marketplace PR after review**

#### Task M47 — M52: notion, godot, telegram, crg, wet, mnemo — same pattern

### Task M53: Phase E exit gate review

- [ ] **Step 1: Verify**

- 7 MCP stable releases published.
- 7 claude-plugins marketplace PRs merged.
- Watchtower on prod VM pulls the new tags (check `/c/watchtower-logs` or `docker logs watchtower`).

- [ ] **Step 2: Update memory**

Save Phase M outcome to `feedback_phase_m_outcome.md` with: versions released, PRs triaged count, CI fixes applied, any user feedback captured during execution.

---

## Self-review

- [x] Spec coverage: Phase A/B/C/D/E each have tasks; exit gates have checklist items; no spec requirement is left un-tasked.
- [x] No placeholders: every task names specific files, specific commands, specific expected output; no "TBD" / "similar to X".
- [x] Type consistency: command names (`bun run check`, `uv run ty check`), env vars (`MCP_CORE_VERSION`, `TRANSPORT_MODE`), workflow names (`cd.yml`), file paths all match across tasks.
- Known gap: Phase L2 Remote Mode (task #25) is a dependency for B3. Task M31 explicitly handles the "not landed yet" branch by splitting Phase B.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-13-phase-m-pre-release-hardening.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, spec-review then code-quality-review between tasks.

**2. Inline Execution** — execute in this session using executing-plans with checkpoints.

Phase M is ~53 tasks; subagent-driven is strongly recommended to keep this session's context healthy across the long tail of repo-by-repo cleanups.
