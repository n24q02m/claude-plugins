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

- **Paste-token**: single textarea for an API token (`wet-mcp` GitHub PAT, `mnemo-mcp` GDrive client_secret JSON).
- **OAuth-redirect**: button "Sign in with Notion / Google / Microsoft" that takes you to the upstream OAuth provider, returns to `/oauth/callback`, then redirects back to your client.
- **Multi-field**: paste multiple tokens at once (`better-email-mcp` with separate IMAP and SMTP credentials).

The same form is rendered in `local-relay` and `remote-relay` for the same server. Storage scope differs; UX is identical.

## Anti-patterns

- Skipping the form when env vars are present — env vars are for `stdio` mode only. Relay modes always go through the form.
- Auto-filling form values from env at relay startup — bypasses the consent step.
- Multiple browser tabs opening for one auth attempt — a known bug (PR #116). The fix: server respects existing daemon's session before spawning a new browser.
