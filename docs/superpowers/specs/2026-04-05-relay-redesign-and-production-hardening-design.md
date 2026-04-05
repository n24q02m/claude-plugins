# Production Hardening & Relay Redesign

**Date**: 2026-04-05
**Status**: Draft
**Scope**: 10 repos (7 MCP servers + mcp-relay-core + claude-plugins + n24q02m profile)

---

## 1. Objectives

11 first-class objectives, derived from `task2.txt` (10 items) + relay redesign (1 item):

| # | Objective | Source | Scope |
|---|-----------|--------|-------|
| **O1** | README + GitHub details accurately reflect code reality | task2 #1 | All 10 repos |
| **O2** | Resolve open issues/PRs/security alerts | task2 #2 | All repos |
| **O3** | lint/check/ci/test all pass, no flaky tests | task2 #3 | All 10 repos |
| **O4** | Coverage ≥95% on all code repos | task2 #4 | 7 code repos (+ relay-core) |
| **O5** | GitHub profile sync with productions list | task2 #5 | n24q02m profile |
| **O6** | Add "Quick Install (Claude Code)" + MCP design philosophy | task2 #6 | n24q02m profile |
| **O7** | Add GWM/Akasha direction section (klprism.com → getaiora.com) | task2 #7 | n24q02m profile |
| **O8** | Profile website at profile.n24q02m.com | task2 #8 | n24q02m profile |
| **O9** | Tests pass on Windows + Linux + macOS | task2 #9 | All code repos |
| **O10** | Fix better-notion-mcp connection issue | task2 #10 | better-notion-mcp |
| **O11** | Relay redesign: non-blocking lifespan, lazy trigger, state machine | session finding | 6 relay-capable MCP repos |

Each objective is a first-class deliverable with own acceptance criteria.

---

## 2. O1 — README + GitHub Accuracy

### Problem
README claims may drift from code (tool counts, version compat, feature list). Example from earlier session: godot description claimed "17 tools" — need to verify.

### Work
For each of 10 repos:
- Compare README feature list against actual `src/` implementation
- Verify tool counts in descriptions (introspect server tool registration)
- Update `repository.description`, `topics`, `homepage` on GitHub
- Verify `marketplace.json` descriptions match each plugin's plugin.json

### Acceptance
- 10 repos: README claims match code (verified via grep + manual review)
- GitHub repo metadata matches README
- marketplace.json aligns with individual plugin.json files

---

## 3. O2 — Issues/PRs/Security Resolution

### Problem
Jules AI and other bots continue generating PRs. Open issues pile up. Security alerts (Dependabot/Renovate) may be pending.

### Work
- Review all open issues in 10 repos (read each thread)
- Review all open PRs in 10 repos (**read every diff** per feedback rule `feedback_review_all_prs.md`)
- Accept / close / fix per merit
- Address Dependabot + Renovate security alerts

### Acceptance
- 0 open issues (except Renovate Dashboard auto-PR)
- 0 open PRs that have been superseded or are no longer applicable
- 0 open high-severity security alerts

---

## 4. O3 — CI/Test/Lint Reliability

### Problem
Pre-commit hooks must pass. CI must be green on main. No flaky tests.

### Work
- Run pre-commit hooks locally on each repo, fix any violations
- Inspect CI runs, fix flaky tests
- Lock test timeouts, deterministic test data

### Acceptance
- All 10 repos: `mise run lint` + `mise run test` green locally
- CI green on main (3 consecutive runs to confirm non-flaky)

---

## 5. O4 — Coverage ≥95%

### Problem
Coverage floor enforced in `CLAUDE.md` (global). Need to verify all code repos hit it.

### Work
- Run coverage tool on each repo
- Identify uncovered branches/lines
- Add targeted tests
- Enforce 95% floor in CI config (fail build if below)

### Acceptance
- 7 code repos (+ mcp-relay-core): coverage ≥95%
- CI enforces floor (PR fails if drops below)

---

## 6. O5 — Profile Productions List Sync

### Problem
https://github.com/stars/n24q02m/lists/productions lists public repos. Profile README must accurately describe each.

### Work
- Audit productions list vs profile README
- Fix descriptions, badges, links
- Ensure listing order makes sense (active vs archived, priority)

### Acceptance
- Every repo in productions list appears in profile README with correct description
- No stale/archived repos listed as active

---

## 7. O6 — Profile: Quick Install + MCP Design Philosophy

### Problem
Profile "MCP Servers & Plugins" section needs installation instructions + explanation of design principles.

### Work
- Add **Quick Install (Claude Code)** block to existing "MCP Servers & Plugins" section:
  ```
  /plugin marketplace add n24q02m/claude-plugins
  /plugin install wet-mcp@n24q02m-plugins
  /plugin install mnemo-mcp@n24q02m-plugins
  ...
  ```
- Add MCP design philosophy paragraph (pull from `skills/fullstack-dev/references/mcp-server.md`):
  - Composite/mega tool pattern
  - 3-tier token optimization
  - Zero-knowledge relay E2E encryption
  - Degraded mode operation
  - Multi-user HTTP with DCR
  - Stdio single-user vs HTTP multi-user isolation
  - Auto-detect with fallback chains
  - Composable via MCP resources

### Acceptance
- Profile README has Quick Install code block (copy-paste ready)
- Design philosophy paragraph (≥8 principles) visible in "MCP Servers & Plugins"

---

## 8. O7 — Profile: GWM/Akasha Direction Section

### Problem
Profile needs section explaining personal long-term direction: klprism.com (step 1) → getaiora.com (step 2) → GWM/Akasha (vision).

### Work
- Add new top-level section "Long-term Direction" to profile README
- Reference `memory/akasha-gwm-roadmap.md` for accurate phasing
- Link to klprism.com + getaiora.com (when live)
- Brief explanation of GWM (Graph World Model) + Akasha vision
- Phase dates (Q4 2026 → 2028)

### Acceptance
- Profile README has new "Long-term Direction" section
- Accurately describes 3-step journey
- No model names leaked per feedback rule

---

## 9. O8 — Profile Website at profile.n24q02m.com

### Problem
Profile README is text-only. User wants interactive website.

### Work
- Scaffold project: Astro + MDX (SSG, fast, MDX for interactive components)
- Content sources: profile README, memory/*.md summaries (public-safe excerpts), repo metadata via GitHub API
- Sections:
  - Hero + bio
  - MCP Servers & Plugins (with live install commands)
  - Long-term Direction (GWM/Akasha)
  - Productions list (live from GitHub API)
  - Tech stack / skills matrix
- Styling: Tailwind + custom theme (inspired by KnowledgePrism brand)
- Deploy: Cloudflare Pages with automatic CI/CD from push
- DNS: `profile.n24q02m.com` CNAME via Cloudflare
- No Tunnel needed (Pages is already public-edge)

### Acceptance
- Repo `n24q02m/profile-site` created (or subdir in `n24q02m`)
- profile.n24q02m.com accessible publicly
- Build on push to main
- Lighthouse score ≥95 (perf + a11y)

---

## 10. O9 — Cross-OS Tests (Windows/Linux/macOS)

### Problem
Tests may assume Linux/macOS behavior (paths, file perms, commands). Must verify on all 3 major OSes.

### Work
- GitHub Actions matrix per repo: `windows-latest`, `ubuntu-latest`, `macos-latest`
- Python repos: verify Python 3.13 installs cleanly on all 3
- TypeScript repos: verify Node 24 + bun on all 3
- Identify OS-specific test failures:
  - Windows: path separator, file lock semantics, WSL detection
  - macOS: case-sensitive paths, FS events
  - Linux: /tmp permissions, /etc/machine-id
- Add `@skipif` markers for genuinely-incompatible tests (document why)
- Known issues:
  - wet-mcp SearXNG (lxml) fails on Windows → skip integration tests, run as opt-in
  - config.enc machine_id varies per OS → verify key derivation is stable

### Acceptance
- All 10 code repos: CI matrix runs on 3 OSes
- Green on all 3 for unit tests
- Integration tests may skip on Windows (documented)

---

## 11. O10 — better-notion-mcp Connection Fix

### Problem
User reports: "Better notion server có vẻ không ổn, không kết nối được"

### Work
- Reproduce connection failure in Claude Code
- Investigate via:
  - Claude Code debug log (MCP connection events)
  - Server stderr on startup
  - Check stdio mode vs HTTP mode default
- Common candidates:
  - Missing `NOTION_TOKEN` env var triggers relay blocking
  - HTTP mode OAuth flow not completing via claude.ai proxy
  - Tool schema incompatibility with Claude Code version
- Add regression test for detected failure mode

### Acceptance
- Root cause documented
- Fix merged + released
- Connects reliably from Claude Code (verified via 3 fresh startup cycles)

---

## 12. O11 — Relay Redesign

### Problem

Current `ensure_config()` blocks `_lifespan_startup()` for 300s (wet/mnemo) / 120s (crg/telegram/email/notion) when no env vars and no saved config. Claude Code MCP handshake timeout (~30s) → connection fails → retry loop → relay rate limit (10 sessions/IP/10min) → cascading failures.

**Additional problems**:
- Setup URL printed to stderr → Claude Code doesn't surface stderr → user never sees URL
- Silent local fallback on timeout → user doesn't know cloud mode failed
- No way to explicitly skip relay persistently → triggers on every startup

### Design

**Unified credential resolution chain** (all 6 relay-capable servers):

```
1. ENV VARS (old path, highest priority)
   → if cloud keys present, state=configured, done
2. SAVED CONFIG
   - stdio: ~/.config/mcp/config.enc[server_name] (AES-256-GCM, machine-bound)
   - http: server-side per-user credential store (AES-256-GCM, user-bound)
   → if present, state=configured
3. LOCAL MODE MARKER (user explicitly skipped)
   - stdio: config.enc[server_name]["_mode"] == "local"
   → state=local, no relay trigger
4. NOTHING FOUND
   → state=awaiting_setup
   → server starts fast (<100ms), tools return setup URL when called
```

**State machine**: `awaiting_setup → setup_in_progress → (configured | local) → (reset → awaiting_setup)`

**Non-blocking lifespan**: removes `await ensure_config()` from startup path. Lifespan only calls fast local checks. Server responds to MCP `initialize` within 100ms.

**Lazy trigger**: When cloud-requiring tool called in `awaiting_setup` state:
- Start relay session (or reuse via file lock)
- Try `webbrowser.open(url)` with WSL detection
- Return tool response with `setup_url` field → Claude Code renders clickable link

**Setup tool extensions**: Add `status | start | skip | reset | complete` actions to existing `setup` tool in each server.

**Session reuse via file lock**: `~/.config/mcp/relay-session-<server>.lock` stores active session. Prevents rate limit across parallel processes.

**Security models** (distinct for stdio vs HTTP):
- **stdio (single-user)**: PBKDF2(machine_id + username, 600k iter) → local file `~/.config/mcp/config.enc`. Threat model: protect against other users on same machine.
- **HTTP (multi-user)**: PBKDF2(server_master_secret + user_id, 600k iter) → server-side KV store per user. Threat model: user A cannot decrypt user B's creds.
- **HTTP OAuth (notion)**: OAuth 2.1 PKCE via claude.ai proxy, server-side token per user.

### Acceptance

- 6 relay-capable MCP servers: lifespan startup <1s (measured via E2E MCP initialize handshake)
- 0 "Failed to reconnect" errors in Claude Code across 5 consecutive fresh restarts
- Setup URL visible in Claude Code UI when triggered (clickable link)
- `setup(action=skip)` persists local mode across restarts
- `setup(action=reset)` clears state and re-triggers relay
- env var users zero-impact (regression tested)
- config.enc users zero-impact (regression tested)

### Affected repos

wet-mcp, mnemo-mcp, better-code-review-graph (Python stdio)
better-telegram-mcp (Python stdio + HTTP)
better-email-mcp, better-notion-mcp (TypeScript stdio + HTTP)
mcp-relay-core (Python + TypeScript core libraries)

---

## 13. Cross-cutting Concerns

### Backward compatibility

All 11 objectives must preserve:
- Existing env var users → zero change
- Existing config.enc users → zero change
- Existing HTTP relay users → zero change
- Existing OAuth users (notion HTTP) → zero change

### Testing strategy

- Unit tests per changed module (≥95% coverage floor)
- Integration tests for each credential flow
- E2E MCP handshake tests (measure startup latency)
- Cross-OS CI matrix for all code repos
- Security tests for multi-user HTTP isolation

### Rollout strategy

- Per-repo beta releases first, then stable after 48h observation
- Document new behaviors in each repo's AGENTS.md + CLAUDE.md
- Release notes call out breaking-ness (expected: zero breaking changes)

---

## 14. Non-Goals

- Multi-credential per server (one active credential set)
- Credential portability across machines
- Auto-renewal of expired API keys
- GUI setup wizard (CLI/MCP only)

---

## 15. Open Decisions

1. **Lock file location**: `~/.config/mcp/` vs `~/.cache/mcp/` (platformdirs `user_config_dir` vs `user_cache_dir`)
2. **Relay session TTL**: enforce client-side (300s) vs respect server-side TTL announcement
3. **`reset` action safety**: require `force=true` parameter to prevent accidental credential wipe
4. **Profile website stack**: Astro + MDX (current choice) vs Next.js + MDX vs SvelteKit
5. **Profile website hosting**: Cloudflare Pages vs Vercel vs GitHub Pages

---

## 16. References

- Spec: `2026-04-01-e2e-mcp-plugin-testing-design.md` (P0-P4 relay audit)
- Spec: `2026-04-03-consolidated-issue-pr-resolution-design.md` (PR resolution rules)
- Memory: `akasha-gwm-roadmap.md`, `virtual-company-design.md`
- Memory: `feedback_review_all_prs.md`, `feedback_never_bulk_close.md`
- User input: `C:\Users\n24q02m-wlap\Downloads\task2.txt`
