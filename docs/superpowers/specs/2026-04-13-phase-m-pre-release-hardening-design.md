# Phase M — Pre-Release Hardening & Stable Release Cut

**Status:** ready for plan
**Date:** 2026-04-13
**Scope:** All 12 repos in the n24q02m MCP ecosystem (7 MCP servers + mcp-core + claude-plugins + qwen3-embed + web-core + n24q02m profile)
**Predecessor:** Phase L (multi-step auth + core-ts parity, commits across mcp-core/email/notion/godot/telegram/mnemo/wet on 2026-04-12..13)

## Goal

Bring every repo in the ecosystem to a clean, green, release-ready state, then cut stable releases for mcp-core and all 7 MCP servers in dependency order. Every transition must be verified end-to-end; a failure at any checkpoint blocks the release until fixed and re-verified.

## Why now

Phase L left 31 unpushed commits across 7 repos, 2 repos with uncommitted changes (notion 18 files, crg 3 files), several repos with red CI on `main`, and ~185 open auto-generated PRs from Sentinel/Bolt/Palette/Jules/Renovate agents. Releasing on top of this state would ship unreviewed code, skip security triage, and break the claude-plugins marketplace consumers.

## Scope (12 repos)

**MCP servers (7):** `better-email-mcp`, `better-notion-mcp`, `better-telegram-mcp`, `better-godot-mcp`, `better-code-review-graph`, `wet-mcp`, `mnemo-mcp`

**Shared infra (5):** `mcp-core`, `claude-plugins` (marketplace), `qwen3-embed`, `web-core`, `n24q02m` (profile)

## Current state (audited 2026-04-13)

### Uncommitted / unpushed work

| Repo | Dirty files | Unpushed commits |
|---|---|---|
| mcp-core | 0 | 15 |
| better-email-mcp | 0 | 5 |
| better-notion-mcp | **18** | 1 |
| better-telegram-mcp | 0 | 5 |
| better-godot-mcp | 0 | 1 |
| better-code-review-graph | **3** | 0 |
| wet-mcp | 0 | 1 |
| mnemo-mcp | 0 | 1 |
| claude-plugins | 0 | 2 |

**Total:** 31 unpushed commits + 21 dirty files across 2 repos.

### Lint / type / test

| Repo | Tests | Lint | Type |
|---|---|---|---|
| mcp-core | 185 TS + 216 PY pass | clean | clean |
| better-email-mcp | 515 pass | clean | clean |
| better-notion-mcp | 721 pass | clean (dirty tree) | clean |
| better-telegram-mcp | 519 pass | clean | **4 `ty` diagnostics** |
| better-godot-mcp | 682 pass | **14 biome errors** | n/a |
| better-code-review-graph | pass | clean | **49 `ty` diagnostics** |
| wet-mcp | 1443 pass | clean | clean |
| mnemo-mcp | 741 pass | clean | clean |
| qwen3-embed | uv resolve FAIL locally | n/a | n/a |
| web-core | 516 collected | clean | n/a |
| claude-plugins | marketplace validate OK | n/a | n/a |
| n24q02m | n/a | n/a | n/a |

### CI on `main`

| Status | Repos |
|---|---|
| **RED recurring** | wet (4 consecutive), telegram (all recent) |
| **RED since 2026-04-09** | qwen3-embed |
| **Latest push failed** | mcp-core, claude-plugins (`cd.yml`) |
| Intermittent | email, notion, godot, crg, mnemo |
| Green | web-core, n24q02m |

### Security alerts (Dependabot / CodeQL+Semgrep / secret-scanning)

- `mcp-core`: 1 Dependabot, 0 code-scanning, 0 secret-scanning.
- All other 11 repos: 0 / 0 / 0.

### Open issues (by theme)

- Dependency Dashboard (Renovate noise): 11 repos
- `[Phase 3] Unified MCP Core migration` coordination: 11 repos
- `qwen3-embed v2.0.0 upgrade`: 3 Python repos (crg, wet, mnemo)
- Other: email #364 (HTTP relay OAuth proxy), telegram #245 (HTTP relay OAuth proxy), notion #322 (Clarvia badge), qwen3-embed #495 (v2.0 feature), claude-plugins #116 (migration hub)

### Open PRs (totals by repo)

| Repo | Bot (Renovate) | Human / Sentinel / Bolt / Palette / Jules | Total |
|---|---|---|---|
| better-notion-mcp | 5 | 23 | **28** |
| better-godot-mcp | 4 | 23 | **27** |
| better-telegram-mcp | 5 | 16 | **21** |
| wet-mcp | 5 | 16 | **21** |
| better-email-mcp | 4 | 16 | **20** |
| mnemo-mcp | 4 | 16 | **20** |
| better-code-review-graph | 3 | 14 | 17 |
| qwen3-embed | 3 | 10 | 13 |
| web-core | 3 | 6 | 9 |
| claude-plugins | 1 | 8 | 9 |
| mcp-core | 0 | 3 | 3 |
| n24q02m | 0 | 0 | 0 |
| **Total** | **37** | **151** | **188** |

Many are semantic duplicates (same Sentinel security finding opened multiple times across dates, overlapping Bolt perf suggestions, stale Palette UX PRs).

## Approach

Five sequential phases; each phase has a strict entry/exit gate. If any gate fails we fix root cause, re-run the phase, and only then advance.

### Phase A — Cleanup (repo-by-repo)

**A0. Push & commit pending work.** Commit the 21 dirty files in notion + crg. Push the 31 unpushed commits across 9 repos. Each push triggers CI; wait for CI to report before moving the repo to A1.

**A1. Fix local lint/type.** godot 14 biome errors, telegram 4 `ty`, crg 49 `ty`, qwen3-embed `requires-python` floor mismatch. After each fix, re-run the full local lint/type/test cycle for that repo and commit fixes.

**A2. Fix CI failures on `main`.** For every red repo, pull the failing run via `gh run view --log-failed`, diagnose root cause, fix in the repo, push, confirm the next main-push run is green. wet (4x), telegram (all), qwen3-embed (since 04-09), claude-plugins `cd.yml`.

**A3. Triage PRs.** Sweep the 188 open PRs in **this exact order** per repo:

1. **Renovate PRs** that are MERGEABLE + have green required checks → merge.
2. **Dependabot PRs** (if any) — same rule.
3. **Bot security PRs (Sentinel, Semgrep)** — read the diff, validate the finding is real, merge the freshest per distinct finding, close the older duplicates with a comment linking to the kept PR.
4. **Bot perf PRs (Bolt)** — benchmark or code-review the suggestion; merge if it demonstrably helps and has tests, close otherwise.
5. **Bot UX PRs (Palette)** — same as Bolt: evidence or close.
6. **Jules / n24q02m-authored test-coverage PRs** — rebase + merge if they raise coverage without masking real bugs.
7. **External contributor PRs** (e.g. telegram #277 `OdinYkt Shared HTTP Event Relay`) — handle individually, never auto-close.
8. Anything still UNKNOWN mergeable after the above — rebase or ask; do not force-close.

**A4. Issue triage.** Close any resolved tracking issues (migration coordinators if Phase L delivered their scope, duplicate dashboards, superseded feature requests). Leave Renovate Dependency Dashboard issues alone — they self-update.

**A5. Security posture confirm.** Re-run the `gh api dependabot/alerts + code-scanning/alerts + secret-scanning/alerts` probe. Must be zero across all 12 repos (the one mcp-core Dependabot alert gets addressed in A1 or A3). Fail the phase gate otherwise.

**Exit gate for Phase A:** across all 12 repos — clean working tree, no unpushed commits, green CI on `main`, zero failing lint/type/test, zero open security alerts, PR queue reduced to "things we actively want to merge or external contributions we are waiting on".

### Phase B — Full E2E verification (17 configurations)

Test every MCP server in every transport mode it supports. No skipping, no "same as last run" — each combination gets a fresh server process, fresh credential state, and at least one real tool call proving the transport + auth + backing service all work end-to-end.

**B1. 7 × local HTTP mode** (`TRANSPORT_MODE=http`, open `/authorize?...`, submit credentials via the relay form, auth where applicable, call a tool, verify).

**B2. 7 × stdio-proxy mode** (`mcp-stdio-proxy` forwarding to the HTTP server; connect a stdio-only client, call a tool, verify).

**B3. 3 × remote HTTP mode** — telegram, email, notion — multi-user remote deployment mode (the Phase L2 Remote Mode task still pending). Each one needs the OAuth 2.1 + DCR flow exercised against a public URL with a real MCP client (Claude Code).

**Exit gate for Phase B:** all 17 configurations pass; at least one tool call proves end-to-end correctness per config; any failure is root-caused, fixed, and the entire affected phase is re-run (not just the failed config).

### Phase C — Release mcp-core stable

Precondition: Phase B exit gate met.

- Dispatch `cd.yml` with `release-channel = stable`.
- PSR v10 computes next version from commit history, publishes npm `@n24q02m/mcp-core` and PyPI `n24q02m-mcp-core` + `mcp-embedding-daemon` + `mcp-stdio-proxy`, pushes Docker multi-arch (amd64+arm64) to DockerHub + GHCR, registers on MCP Registry, creates a GitHub release.
- Verify: `npm view`, `pip index versions`, image digests on GHCR, MCP Registry page all show the new version.

**Exit gate for Phase C:** new mcp-core version exists on all distribution targets and is installable.

### Phase D — Bump mcp-core in 7 MCP servers + full re-test

- For each of the 7 MCP repos: bump `@n24q02m/mcp-core` in `package.json` (TS: email, notion, godot) and `n24q02m-mcp-core` in `pyproject.toml` (Python: telegram, crg, wet, mnemo) to the version cut in Phase C.
- Refresh lockfiles (`bun install` / `uv lock`).
- Re-run Phase A1 smoke (lint/type/test) per repo.
- Re-run the 17-configuration Phase B grid.
- Any failure → fix root cause in mcp-core or the consuming repo, repeat Phase C if the fix is in mcp-core (cut a point release) and D in sequence. Do not patch only the consumer and skip a mcp-core release.

**Exit gate for Phase D:** all 7 repos pin the new mcp-core, all 17 Phase B configurations pass.

### Phase E — Release 7 MCP servers stable

- Dispatch `cd.yml` / `release.yml` with `stable` channel for each of the 7 MCP repos in a safe order — mcp-core consumers first (email, notion, godot on TS; telegram, crg, wet, mnemo on Python) so any late-stage integration break surfaces per-repo.
- Each release pipeline: PSR v10 → PyPI/npm publish → Docker multi-arch (amd64+arm64) to DockerHub + GHCR → MCP Registry → GitHub Release → marketplace.json bump in claude-plugins.
- Verify every target: npm/PyPI, GHCR images, MCP Registry, marketplace.json PR merged.

**Exit gate for Phase E:** 7 MCP servers shipped stable; claude-plugins marketplace points at the new versions; Watchtower on prod VM pulls them within the watch window.

## Ordering & dependency notes

- **Phase A must complete across ALL 12 repos** before Phase B begins. Partial A → partial B would hide cross-repo interactions (shared mcp-core fix landing mid-test run, etc.).
- **Phase C blocks D; D blocks E.** An mcp-core bug found in Phase D requires going back to C for a new point release.
- **claude-plugins, qwen3-embed, web-core, n24q02m** don't ship MCP servers, but their Phase A cleanup is still required because they participate in the marketplace and cross-repo dependency graph.

## Non-goals (explicitly out of scope)

- New features. Phase M is stabilization only.
- Changing the release pipeline. PSR v10 stays as-is.
- Migrating to a new OAuth surface. Phase L's multi-step auth is the final shape.
- Closing tracking issues that are still doing useful work (Dependency Dashboard, active `[Phase 3]` coordinators).

## Open questions

- **Bot PR merge authority:** for Sentinel/Bolt/Palette/Jules PRs with genuine fixes, should we auto-accept after single-pass review, or require a fresh code-review subagent on every one? Default to subagent review until a rule gets added to the `feedback` memory.
- **qwen3-embed Python floor:** bump `requires-python` to `>=3.11` aligning with numpy 2.4.4, vs. pinning numpy `<2.4` to stay on 3.10? Prefer the floor bump — 3.11 is two years old.
- **Remote mode scope:** task #25 (Phase L2 Remote Mode) is listed but has no landed implementation yet. Phase B3 presumes it exists. If remote mode is not implemented by the time Phase B starts, split B into B-local+B-stdio (7 + 7) first and track B-remote as a Phase M.2 follow-up.

## Deliverables

- Clean working tree on all 12 repos.
- Green CI on `main` for all 12 repos.
- Zero open security alerts across the ecosystem.
- Actively-reviewed PR queue (no stale bot duplicates).
- mcp-core stable release published + consumed.
- 7 MCP server stable releases published + available in the marketplace.
- Updated `MEMORY.md` entry with the Phase M outcome and any feedback the user provided during execution.
