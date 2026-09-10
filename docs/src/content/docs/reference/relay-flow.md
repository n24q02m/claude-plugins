---
title: Relay flow
description: Credential bootstrap state machine for local-relay and remote-relay modes.
---

Relay is the server's response when a tool needs credentials and none exist yet (or the existing ones are invalid). The same flow runs in `local-relay` (single-user, file-backed) and `remote-relay` (multi-user, per-JWT-sub backend). Only the storage scope differs.

## State machine

```
        +-------------+
        |   client    |
        |  invokes    |
        |   tool()    |
        +------+------+
               |
               v
   +-----------+----------+
   | server has creds for |
   | this user/scope?     |
   +---+--------------+---+
       | yes          | no
       v              v
   +-------+    +------------+
   | run   |    | return     |
   | tool  |    | "needs     |
   +-------+    | auth" +    |
                | redirect   |
                | URL        |
                +-----+------+
                      |
                      v
              +-------+--------+
              | client opens   |
              | URL in browser |
              +-------+--------+
                      |
                      v
              +-------+--------+
              | user fills     |
              | form on        |
              | server's       |
              | /authorize     |
              +-------+--------+
                      |
                      v
              +-------+--------+
              | server         |
              | encrypts +     |
              | stores creds,  |
              | returns 302    |
              | to client's    |
              | redirect_url   |
              +-------+--------+
                      |
                      v
              +-------+--------+
              | client retries |
              | original tool  |
              | call (now has  |
              | creds)         |
              +----------------+
```

## Endpoints (per server)

- `GET /authorize` — render the credential form. Required query: `?redirect_url=<client-callback>`. Optional: `?state=<csrf>`.
- `POST /authorize` — accept submitted credentials, encrypt, persist, redirect to `redirect_url`.
- `GET /healthz` — liveness probe.
- `GET /.well-known/oauth-authorization-server` — only in `remote-oauth` mode.

## What `redirect_url` does

After credential submission, server calls `window.location.replace(redirect_url)` so the user's browser tab returns to the client's "we've got your creds, retrying tool call now" page. **Do not** show a static "you can close this tab" message — the browser must follow the redirect back to the client so the tool call retries automatically.

## What encryption is used

Server generates a per-server AES-256-GCM key at first run, stored in:

- `local-relay`: `~/.config/<server>/keyring.enc` (protected by OS keyring on macOS/Windows; XDG-locations on Linux)
- `remote-relay` / `remote-oauth`: derived from a server-startup secret (typically loaded from `KEYRING_SECRET` env var, which itself comes from your secret manager — Doppler / Infisical / [`skret`](https://skret.n24q02m.com))

## What the form looks like

Form fields are server-specific. Common patterns:

- **Provider credentials**: provider-specific API keys and model settings. Google Drive uses an OAuth flow on eligible non-CF Wet/Mnemo hosts, not a pasted client-secret JSON requirement.
- **OAuth-redirect**: button "Sign in with Notion / Google / Microsoft" that takes you to the upstream OAuth provider, returns to `/oauth/callback`, then redirects back to your client.
- **Multi-field**: paste multiple tokens at once (`better-email-mcp` with separate IMAP and SMTP credentials).

The same form is rendered in `local-relay` and `remote-relay` for the same server. Storage scope differs; UX is identical.

## Managed Cloudflare model configuration

Wet, Mnemo, and CRG keep model selection, provider API bases, and keys in the
authenticated subject's relay configuration. Server-side LiteLLM library
calls go through Cloudflare AI Gateway to the upstream provider; there is no
standalone LiteLLM proxy. A process-wide Worker model pin must not override
that subject's selection.

| Capability | Selection | Applicable servers |
|---|---|---|
| Completion | `openrouter/minimax/minimax-m3:free` | Wet/Mnemo `LLM_MODELS`; CRG `SUMMARY_MODELS` |
| Embedding | `cohere/embed-v4.0` | Wet, Mnemo, CRG `EMBEDDING_MODELS` |
| Reranking | `cohere/rerank-v4.0-fast` | Wet and Mnemo `RERANK_MODELS` |

Configure the provider-appropriate gateway base in `LLM_API_BASE`,
`EMBEDDING_API_BASE`, or `RERANK_API_BASE` alongside the matching key in the
same subject's relay form. CRG has no cloud rerank consumer; its query reranker
is local and opt-in through `LOCAL_RERANK_MODEL`.

Wet's hosted `SEARCH_BACKENDS` chain and search-provider keys are subject-owned
too. Select the chain explicitly in the relay form (for example,
`tavily,duckduckgo,startpage` with that subject's Tavily key); the Worker does
not forward operator search/model chains or provider keys as user defaults.
An empty subject configuration remains empty rather than borrowing another
account's credentials. Operator-owned Browser Run settings are separate:
they select extraction renderers, not native interactive browser sessions.

The completion selection is a single free-model route: no GLM, Jina, paid
completion, or silent completion fallback. Cohere embedding and reranking
are **paid**, not free fallbacks. Before making calls, verify current pricing,
obtain explicit authorization with a spending cap, and retain usage/cost
receipts. Configuration alone is not evidence that a provider call or a
deployment succeeded.

Public local stdio and SearXNG capabilities remain available. They are not
the managed personal Wet configuration, and these server settings never
change user-owned OMP model/profile settings. Google Drive synchronization is
disabled when Wet uses `DOCS_DB_BACKEND=cf-d1` or Mnemo uses
`MEMORY_DB_BACKEND=cf-d1`; do not start its wizard, device-code flow, or
auto-sync on those hosts. Non-CF Google Drive sync remains an explicit
operator choice.

## Anti-patterns

- Skipping the form when env vars are present — env vars are for `stdio` mode only. Relay modes always go through the form.
- Auto-filling form values from env at relay startup — bypasses the consent step.
- Multiple browser tabs opening for one auth attempt — a known bug (PR #116). The fix: server respects existing daemon's session before spawning a new browser.
