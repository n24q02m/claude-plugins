# Implementation Plan: Production Hardening & Relay Redesign

**Spec**: `specs/2026-04-05-relay-redesign-and-production-hardening-design.md`
**Date**: 2026-04-05 (updated 2026-04-06)
**Objectives**: 11 (O1-O11)

---

## Design Principles (locked, updated 2026-04-06)

These constraints override any earlier assumptions in T0-T6:

1. **Relay is primary** — the correct and default path for all new users. Never remove, never mark BETA, never demote to secondary.
2. **Env vars are backward compat only** — kept so existing users don't break. Not advertised as preferred.
3. **No `set_env` MCP action anywhere** — credentials must never pass through LLM chat context to a tool call. Relay browser form is the only credential-setting UI.
4. **No auto-fallback to local ONNX** — wet-mcp, mnemo-mcp, crg must not silently fall back when no credentials are configured. AWAITING_SETUP = block (not degrade). LOCAL state (via explicit `skip`) = local OK.
5. **Hook-based automatic credential check** — LLM must automatically (not user manually) call status then open_relay before first tool use per MCP server per session. Implemented via claude-plugins PreToolUse hooks + session state files.
6. **Tool queuing via LLM retry** — hooks deny the original tool call with clear instructions; Claude retries after relay completes. No actual queuing mechanism needed.

---

## Task Tracker

Each objective (O1-O11) maps to one or more implementation tasks. Tasks grouped by phase.

Legend: `[S]` small (<2h), `[M]` medium (2-8h), `[L]` large (>8h)

---

## Phase 0 — Session handoff (do first in new session)

**Goal**: Close out pending work from previous session (2026-04-05), verify baseline state before new work.

### T0.1 [S] Commit pending doc changes (relay as primary)
Uncommitted in 6 MCP repos from previous session:
- `docs/setup-manual.md` + `docs/setup-with-agent.md`: **DO NOT** commit the "swap env vars to primary, mark relay as BETA" direction — that was wrong. Relay is primary.
- `uv.lock`: version sync to released versions (wet 2.22.0, mnemo 1.17.0, crg 3.7.0, telegram 4.2.0)
Repos: wet-mcp, mnemo-mcp, better-code-review-graph, better-telegram-mcp, better-email-mcp, better-notion-mcp
- If setup-manual.md/setup-with-agent.md were changed: revert them to relay-as-primary framing, or update to accurately reflect new design
- claude-plugins: commit updated spec + plan files

### T0.2 [M] Diagnose wet-mcp Claude Code connection failure
Previous session found: wet-mcp fails Claude Code connect 5+ times while mnemo/crg succeed 1 try, even though direct `uvx --python 3.13 wet-mcp` works in <100ms with env vars.
- Reproduce with `claude --mcp-debug` to capture full MCP stderr
- Candidates to check:
  - docs.db file size (1.5GB) causing slow SQLite open on cold filesystem cache
  - uvx lock contention when multiple servers spawn parallel
  - FastMCP version mismatch (serverInfo reports 1.27.0)
  - Zombie process holding resources
- Document root cause + fix

### T0.3 [S] Verify telegram/godot/email load after reinstall
Previous session reinstalled these 3 plugins (they weren't starting from Claude Code). Need verification:
- Run `/mcp` after fresh restart, verify all 7 n24q02m MCP servers connect
- If telegram/godot/email still miss → investigate Claude Code MCP config resolution

### T0.4 [M] E2E tool smoke test across all 7 servers
Verify core tool works for each server (not just connection):
- wet: `search(action="search", query="test")` or `extract`
- mnemo: `memory(action="search", query="test")`
- crg: `config(action="status")` + `graph(action="stats")`
- telegram: `telegram(action="help")` (degraded mode OK without bot token)
- email: `email(action="help")` + `email(action="list_accounts")`
- godot: `godot(action="help")`
- notion: `notion(action="list_databases")` (HTTP mode via claude.ai proxy)
- Document any failures → inform Phase 2 scope

### Acceptance (Phase 0)

- All 6 MCP repos + claude-plugins: pending doc commits pushed to main
- wet-mcp connection root cause documented (may be fixed by Phase 2 relay refactor, may be separate issue)
- All 7 MCP servers verified loading in Claude Code
- 7 servers: core tool smoke test passes

---

## Phase 1 — Baseline health (O3, O4, O9)

**Goal**: Green CI across all 10 repos on all 3 OSes, coverage ≥95%.

### T1.1 [M] Audit + fix pre-commit hooks
- Run pre-commit locally on each of 10 repos
- Fix lint/format/type-check violations
- Ensure hooks enforce `feat:`/`fix:` commit prefix per feedback rule

### T1.2 [L] Add cross-OS CI matrix (O9)
- For each code repo, update `.github/workflows/ci.yml`:
  - Matrix: `os: [ubuntu-latest, windows-latest, macos-latest]`
  - Python repos: `python: ["3.13"]`
  - TypeScript repos: `node: ["24"]` + bun
- Identify + skip genuinely-incompatible tests (e.g. wet-mcp SearXNG lxml on Windows)
- Document skips with OS-specific markers (pytest `@pytest.mark.skipif`, vitest `skip.if`)

### T1.3 [L] Coverage floor ≥95% (O4)
- Per code repo: measure current coverage, identify gaps
- Add tests for uncovered branches
- Enforce 95% floor in CI config (fail PR if drops below)

### T1.4 [S] Verify CI green 3x in a row
- After T1.1-T1.3 merged: trigger CI 3 times per repo
- Investigate any flaky tests, lock down

### Acceptance (Phase 1)
- 10 repos: pre-commit passes locally
- 10 code repos: CI green on 3 OSes × 3 consecutive runs
- 7+ code repos: coverage ≥95%, enforced in CI

---

## Phase 2 — Fix broken things (O10, O11)

**Goal**: Unblock user daily workflow. Connection failures must stop.

### T2.1 [M] Diagnose + fix better-notion-mcp connection (O10)
- Reproduce failure in Claude Code
- Capture debug logs (`claude --mcp-debug`)
- Inspect stdio vs HTTP mode default selection
- Patch root cause + add regression test
- Release stable version, sync to marketplace

### T2.2 [M] mcp-relay-core v1.3.0 — new primitives (O11 dependency)
- Repo: `mcp-relay-core`
- Add `SessionLock` (Python + TypeScript mirror)
- Add `try_open_browser()` with WSL detection (Python + TS)
- Add `local_mode_marker` support in storage (Python + TS)
- Release v1.3.0 (stable channel)

### T2.3 [L] Refactor wet-mcp relay (O11) [PARTIALLY DONE — needs cleanup]
Done in previous session: replace blocking lifespan, add `_require_credentials()` on cloud tools, add `open_relay` action, non-blocking credential state.
Remaining (updated per Design Principles):
- Remove `set_env` action and `set_env_var()` function entirely
- Remove auto-fallback in `_init_embedding_backend()` + `_init_reranker_backend()`:
  - AWAITING_SETUP → init nothing (backend = None)
  - CONFIGURED → cloud only, no local fallback if cloud fails
  - LOCAL → local only
- Update `_require_credentials()` error message: remove set_env option, only mention `open_relay` + `skip`
- Remove `set_env` from valid_actions list and tool description
- Update tests for new behavior (auto-fallback removal, no set_env)
- Release v2.23.0 (stable)

### T2.4 [L] Refactor mnemo-mcp relay (O11) [PARTIALLY DONE — needs same cleanup]
Done in previous session: non-blocking lifespan, credential state, basic blocking.
Remaining (mirror T2.3 remaining work):
- Remove `set_env` action if present
- Remove auto-fallback in embedding/reranking init
- Add `_require_credentials()` to all cloud-requiring tools (memory, config) if not already
- Update tests
- Release v1.18.0 (stable)

### T2.5 [L] Refactor better-code-review-graph relay (O11) [PARTIALLY DONE — needs same cleanup]
Done in previous session: same as mnemo-mcp.
Remaining (mirror T2.3 remaining work):
- Remove `set_env` action if present
- Remove auto-fallback in embedding/reranking init
- Add `_require_credentials()` to all cloud-requiring tools
- Update tests
- Release v3.8.0 (stable)

### T2.3b [M] Hook scripts for automated credential check (claude-plugins)
Implements Design Principle #5/#6 — automatic LLM behavior, no manual user action.
- Add hook scripts to `plugins/{wet-mcp,mnemo-mcp,better-code-review-graph}/hooks/`
  - `check-credentials.sh`: reads session state file + checks config.enc/env vars
  - PreToolUse: fires for all credential-requiring tools (not setup/help)
    - If session verified: allow
    - If config.enc exists or cloud env vars present: allow + write session state
    - Otherwise: deny with reason = "Call setup(action='open_relay'), retry after configuration"
  - PostToolUse for setup tool: if response state = configured/local, write session state file
- Add `hooks/hooks.json` per plugin registering the hooks
- Session state dir: `~/.claude/mcp-state/<session_id>/<server>-credentials`
- Test: simulate first-call flow on clean state

### T2.6 [L] Refactor better-telegram-mcp relay (O11)
- Mirror T2.3 pattern (stdio + HTTP modes)
- Release v4.2.0 (stable)

### T2.7 [L] Refactor better-email-mcp relay (O11, TypeScript)
- Refactor `relay-setup.ts` + `init-server.ts`
- Add `requiresCredentials` middleware in `tools/registry.ts`
- Extend setup tool actions
- Release v1.20.0 (stable)

### T2.8 [L] Refactor better-notion-mcp relay (O11, TypeScript)
- Same as T2.7 but for notion
- Combine with T2.1 fix
- Release stable

### T2.9 [M] HTTP relay security audit (part of O11)
- Verify `better-email-mcp/src/auth/per-user-credential-store.ts` uses 600k PBKDF2 + user_id in key derivation
- Audit `better-telegram-mcp` HTTP relay for equivalent per-user isolation; backport if missing
- Document security model in each repo's AGENTS.md
- Add multi-user isolation tests (user A cannot decrypt user B creds)
- Document master secret rotation procedure

### T2.10 [S] Sync claude-plugins marketplace with new versions
- Update `marketplace.json` plugin versions
- Commit + push
- Verify `claude plugin update --all` pulls latest

### T2.11 [M] E2E verification of relay redesign
- Fresh machine scenario: no env vars, no config.enc
- Install each plugin, verify:
  - MCP connect <1s per server
  - Tool call returns setup URL (clickable in Claude Code)
  - Browser auto-opens (or fallback gracefully)
  - Submit form → config.enc saved → next call uses creds
  - Skip flow → local mode marker saved → restart skips relay
  - env var flow → relay never triggered
  - HTTP relay multi-user flow → user A/B isolated

### Acceptance (Phase 2)
- better-notion-mcp connects reliably in Claude Code
- 6 relay-capable MCP servers: lifespan <1s, 0 "Failed to reconnect" in 5 consecutive restarts
- Setup URL visible in Claude Code UI
- All credential flows verified E2E

---

## Phase 3 — Accuracy (O1, O5)

**Goal**: Docs match reality.

### T3.1 [M] README truth audit (O1)
- For each of 10 repos:
  - Compare README feature list vs `src/` implementation
  - Verify tool counts (introspect plugin + server code)
  - Update repo metadata (description, topics, homepage) via `gh repo edit`
- Verify `marketplace.json` descriptions sync with each plugin.json

### T3.2 [S] GitHub profile productions list sync (O5)
- Audit https://github.com/stars/n24q02m/lists/productions
- Update n24q02m profile README to accurately describe each listed repo
- Fix stale descriptions, badges, links
- Ensure active vs archived ordering makes sense

### Acceptance (Phase 3)
- 10 repos: README matches code (manual review passes)
- Profile productions list section accurate

---

## Phase 4 — Profile enhancements (O6, O7)

**Goal**: Profile README has installation guide + long-term direction.

### T4.1 [M] Quick Install block + MCP design philosophy (O6)
- Add "Quick Install (Claude Code)" subsection to existing "MCP Servers & Plugins":
  ```
  /plugin marketplace add n24q02m/claude-plugins
  /plugin install wet-mcp@n24q02m-plugins
  /plugin install mnemo-mcp@n24q02m-plugins
  /plugin install better-code-review-graph@n24q02m-plugins
  /plugin install better-telegram-mcp@n24q02m-plugins
  /plugin install better-godot-mcp@n24q02m-plugins
  /plugin install better-email-mcp@n24q02m-plugins
  /plugin install better-notion-mcp@n24q02m-plugins
  ```
- Add MCP design philosophy paragraph (≥8 principles, from `skills/fullstack-dev/references/mcp-server.md`)

### T4.2 [M] GWM/Akasha direction section (O7)
- Add new "Long-term Direction" top-level section to profile README
- Reference `memory/akasha-gwm-roadmap.md` for phasing
- Structure: klprism.com (current) → getaiora.com (next) → GWM/Akasha (vision Q4 2026-2028)
- No model names leaked (per feedback rule)

### Acceptance (Phase 4)
- Profile README has Quick Install code block
- Profile README has MCP design philosophy paragraph (8+ principles)
- Profile README has Long-term Direction section with 3-step journey

---

## Phase 5 — Profile website (O8)

**Goal**: profile.n24q02m.com live.

### T5.1 [M] Resolve Open Decision #4-5 (spec §15)
- Framework: Astro + MDX (proposed)
- Hosting: Cloudflare Pages (proposed)
- Confirm with user before scaffolding

### T5.2 [M] Scaffold project
- Create `n24q02m/profile-site` repo (or subdir)
- Astro + MDX + Tailwind
- Initial sections: Hero, MCP Servers & Plugins, Long-term Direction, Productions, Tech Stack
- Pull content from profile README (don't duplicate, render from source)
- Pull productions list from GitHub API

### T5.3 [M] Design + implement
- Custom theme (inspired by KnowledgePrism brand)
- Live install commands (copy-to-clipboard buttons)
- Responsive + a11y
- Lighthouse score ≥95

### T5.4 [S] Deploy
- Connect repo to Cloudflare Pages
- Auto-deploy on push to main
- DNS: `profile.n24q02m.com` CNAME via Cloudflare
- Verify SSL + HTTP→HTTPS redirect

### Acceptance (Phase 5)
- profile.n24q02m.com publicly accessible
- Auto-deploys on main push
- Lighthouse ≥95 (perf + a11y)

---

## Phase 6 — Issue/PR/security cleanup (O2)

**Goal**: 0 open issues/PRs (except Renovate Dashboard), 0 high-severity security alerts.

### T6.1 [L] Review all open issues + PRs in 10 repos
- **Must read every PR diff** (feedback rule `feedback_review_all_prs.md` + `feedback_never_bulk_close.md`)
- Categorize: accept / revise / close with reason
- Process in batches of 10 per repo for manageability
- Close Jules AI PRs per merit (not bulk)

### T6.2 [S] Address security alerts
- Dependabot / Renovate alerts per repo
- Merge security-only updates first
- Verify no breaking changes

### Acceptance (Phase 6)
- 10 repos: 0 open issues (except Renovate Dashboard PR)
- 0 open PRs that shouldn't be open
- 0 open high-severity security alerts

---

## Execution order

```
Phase 0 (handoff: commits + diagnosis + smoke test)
  │
  ├─→ Phase 1 (baseline health) ──┐
  │                               ├─→ unblocks all subsequent phases
  ├─→ Phase 2 (fix broken) ───────┘
  │    │
  │    ├─→ Phase 3 (accuracy) ──┐
  │    │                        ├─→ informs Phase 5 (website needs accurate README)
  │    ├─→ Phase 4 (profile) ───┘
  │    │
  │    └─→ Phase 5 (website)
  │
  └─→ Phase 6 (PR/issue cleanup) [can run parallel with any phase after Phase 0]
```

**Parallel execution**: Phase 6 is independent after Phase 0. Phases 3/4 can overlap. Phase 5 depends on Phase 3/4 content. Phase 0 blocks all others.

---

## Per-objective mapping

| Obj | Tasks |
|-----|-------|
| O1 (README accuracy) | T3.1 |
| O2 (issues/PRs) | T6.1, T6.2 |
| O3 (CI/test/lint) | T1.1, T1.4 |
| O4 (coverage 95%+) | T1.3 |
| O5 (productions sync) | T3.2 |
| O6 (Quick Install + philosophy) | T4.1 |
| O7 (GWM/Akasha direction) | T4.2 |
| O8 (profile website) | T5.1, T5.2, T5.3, T5.4 |
| O9 (cross-OS CI) | T1.2 |
| O10 (notion fix) | T2.1 |
| O11 (relay redesign) | T2.2-T2.11 |

---

## Rollback triggers

- **Phase 2 relay refactor causes connection regressions in >1 server** → revert all 6 server releases, keep core-py/core-ts v1.3.0 (additive only), investigate
- **Phase 1 CI matrix exposes major Windows incompat** → reduce scope to Linux+macOS, document Windows limitations, file follow-up
- **Phase 5 website hosting fails** → fall back to GitHub Pages (built-in, no DNS work)

---

## Out of scope (explicit)

- Building klprism.com or getaiora.com (those are separate projects, only referenced)
- Migrating existing user credentials (zero-impact contract)
- Deprecating env var auth (kept as backward-compat secondary path; never primary)
- Changing plugin.json schema beyond setup tool action additions
- Adding `set_env` or any credential-passing MCP action to any server (permanently excluded)
