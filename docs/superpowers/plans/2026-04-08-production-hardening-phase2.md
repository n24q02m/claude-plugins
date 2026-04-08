# Production Hardening Phase 2

**Date**: 2026-04-08
**Scope**: 7 MCP servers + relay-core + claude-plugins + qwen3-embed + web-core + profile
**Predecessor**: `2026-04-05-relay-redesign-and-production-hardening.md` (Phase 0+2 done)

---

## Task Tracker

### Phase A — Relay bugs from E2E testing

#### A1. Hot-reload credentials after relay setup (mcp-relay-core#188)
All servers require reconnect/restart after relay credentials submitted. Running process doesn't reload IMAP pool / Telethon backend / embedding backend.

**Fix**: After relay background poll saves config, server must re-init service resources:
- Python servers: `setup_complete` already exists but doesn't re-init backend properly (mnemo fixed, wet OK, crg lazy). Need auto-call after poll.
- TS servers (email/notion): no hot-reload mechanism. Need `onCredentialsChanged` callback.

**Repos**: all 6 relay servers + mcp-relay-core

#### A2. Browser auto-open failures (mcp-relay-core#188)
`try_open_browser()` fails silently on Windows. Email lazy trigger doesn't call it at all.

**Fix**: Ensure `try_open_browser()` called in all relay triggers. Add fallback: if browser fails, include clickable URL in tool response.

**Repos**: mcp-relay-core, better-email-mcp, better-notion-mcp

#### A3. Notion relay URL only in stderr, not tool response
Tool response says "set NOTION_TOKEN env var" but relay URL only logged to stderr. User never sees URL in MCP client.

**Fix**: Include relay URL in tool error response (same as email's lazy trigger pattern).

**Repo**: better-notion-mcp

#### A4. Add explicit setup tool to email + notion
wet/mnemo/crg/telegram have setup_start/reset/complete actions. Email + notion only have lazy trigger — no way to manually trigger/reset relay.

**Fix**: Add setup actions to email config tool and notion (new setup tool or extend existing).

**Repos**: better-email-mcp, better-notion-mcp

#### A5. GDrive sync duplicate folders — code fix (mcp-relay-core#188)
When sync_folder_ids.json cache missing, Drive API search returns empty (eventual consistency) → creates new folder. Cleaned duplicates manually but root cause unfixed.

**Fix**: Add retry with exponential backoff before creating new folder. On write, always persist folder ID immediately. Add integration test.

**Repos**: wet-mcp, mnemo-mcp

#### A6. Telegram relay UX: session reuse skips OTP without explanation
When Telethon session file exists, relay reports "complete/authorized" immediately. User confused why no OTP was asked.

**Fix**: Browser relay page should show "Existing session found — already authorized" message instead of generic "complete".

**Repos**: better-telegram-mcp, mcp-relay-core (relay page JS)

#### A7. SearXNG on Windows — SSRF blocks localhost
SearXNG runs on localhost but wet-mcp SSRF protection blocks localhost URLs. Search completely broken on Windows.

**Fix**: Exempt 127.0.0.1/localhost from SSRF check when the target is the local SearXNG instance (check matching SearXNG port). Do NOT disable SSRF globally.

**Repo**: web-core (security.py or equivalent)

---

### Phase B — HTTP relay OAuth proxy (new feature)

#### B1. Design OAuth 2.1 wrapper for relay (mcp-relay-core)
MCP HTTP transport (claude.ai) only supports OAuth or no-auth. Relay needs to act as OAuth Authorization Server.

**Design**:
- Relay form = OAuth authorization page
- Client redirects user to relay URL
- User enters credentials → relay issues authorization code
- Client exchanges code → server issues access token + stores config
- Backward compatible with stdio relay

**Repos**: mcp-relay-core (core), all 6 relay servers (integration)
**Issues**: better-telegram-mcp#245, better-email-mcp#364

#### B2. Implement + test on VM (telegram + email HTTP relay)
Deploy HTTP mode on oci-vm-prod, test multi-user isolation:
- User A authenticates → credentials stored per-user
- User B authenticates → separate credentials
- Verify A cannot access B data

**Repos**: better-telegram-mcp, better-email-mcp
**Infra**: oci-vm-prod, Caddy, CF Tunnel

---

### Phase C — Code quality (from task2.txt)

#### C1. README truth audit — all repos
Compare README feature lists vs actual source code. Fix tool counts, descriptions, badges.
Update repo metadata via `gh repo edit`.

**Repos**: all 12

#### C2. Lint/check/CI/test pass
Ensure all repos have green CI. Fix remaining lint/format issues.
Current status: 5 repos green (agent fixed), others need verification.

**Repos**: all code repos

#### C3. Coverage >= 95%
Add tests for uncovered relay/credential code. Agent lowered thresholds to unblock CI — need to raise back to 95%.

Current: wet-mcp 94%, crg 90% threshold, telegram 91%, web-core 85% threshold.

**Repos**: wet-mcp, better-code-review-graph, better-telegram-mcp, web-core, better-email-mcp

#### C4. Cross-OS CI matrix (ubuntu/windows/macos)
Add matrix strategy to CI workflows. Skip genuinely-incompatible tests with OS markers.

**Repos**: all code repos

#### C5. GitHub profile accuracy
Ensure productions list descriptions match code. Already started (KlPrism fixed).
Verify all public repos have correct descriptions + topics.

**Repo**: n24q02m profile, all production repos

---

### Phase D — Issue/PR/Security cleanup

#### D1. Review remaining 272 open PRs across 9 repos
Must read every diff. Categorize: accept/revise/close. Process lần lượt per repo.

| Repo | Open PRs |
|------|----------|
| wet-mcp | 30 |
| mnemo-mcp | 30 |
| crg | 30 |
| telegram | 30 |
| email-mcp | 30 |
| notion-mcp | 30 |
| godot-mcp | 30 |
| relay-core | 30 |
| claude-plugins | 22 |

#### D2. Resolve open issues (14 total)
Review and resolve/close all open issues across 9 repos.

#### D3. Address security alerts
- crg: 5 alerts (fastmcp SSRF/command injection/OAuth, Pygments ReDoS)
- mnemo-mcp: 1 alert (Pygments ReDoS)
- relay-core: 1 alert

Fix: update dependencies to patched versions.

---

### Phase E — Profile website

#### E1. Scaffold profile.n24q02m.com
Framework: Astro + MDX. Hosting: Cloudflare Pages.
Sections: Hero, MCP Servers, Design Philosophy, Long-term Direction, Productions, Tech Stack.

#### E2. Design + implement
Pull content from profile README. Productions list from GitHub API.
Responsive + a11y. Lighthouse >= 95.

#### E3. Deploy
DNS: profile.n24q02m.com CNAME via Cloudflare.
Auto-deploy on push to main.

---

### Phase F — Notion connection fix (from task2.txt item 10)

#### F1. Diagnose + fix better-notion-mcp connection
"Better notion server has issues, cannot connect" — original plan T2.1.
Investigate stdio vs HTTP mode default selection. Capture debug logs.

**Repo**: better-notion-mcp

---

## Execution order

```
Phase A (relay bugs) — blocking, fix first
  |
  +--> Phase B (HTTP relay OAuth) — after A, design + implement
  |
  +--> Phase C (code quality) — parallel with B
  |     |
  |     +--> Phase E (website) — after C5 profile accuracy done
  |
  +--> Phase D (PR/issue/security) — parallel, independent
  |
  +--> Phase F (notion fix) — parallel, independent
```

Phase A blocks B (relay must work before adding OAuth).
Phase C5 informs E (website needs accurate README content).
D and F are independent, can run anytime.
