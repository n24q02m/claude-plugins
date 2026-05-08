---
title: Multi-user setup
description: Self-host one server, share with a team — each user has own credentials.
---

In `remote-relay` and `remote-oauth` modes, an MCP server stores credentials **per JWT subject** (the `sub` field of the bearer token your client sends). One deployed server serves N users without leaking creds across users.

## How it works

1. Each user authenticates against your deployed server. They get a JWT with their `sub` (typically email or GitHub username).
2. When the user first invokes a tool that needs credentials (e.g. Notion API key), the server detects no credentials exist for that `sub` and triggers the relay flow — opens a browser at `https://<server>.your-domain/authorize`.
3. The user fills the form (paste API token, OAuth login, etc.). Server encrypts and stores under key `<server-name>:<sub>`.
4. Subsequent tool invocations from the same user route to the same encrypted bundle.

## Deployment

Self-hosted via Docker:

```sh
docker run -d \
  -p 8080:8080 \
  -e MCP_TRANSPORT=http \
  -e PUBLIC_URL=https://wet-mcp.your-domain.com \
  -e JWT_PUBLIC_KEY="<your-jwt-public-key>" \
  ghcr.io/n24q02m/wet-mcp:latest
```

Behind any reverse proxy that adds `Authorization: Bearer <token>`. Caddy + Cloudflare Tunnel is the canonical pattern.

## OAuth provider (`remote-oauth` mode)

Server doubles as an OAuth Authorization Server. Clients implement standard OAuth 2.1 flow:

```
GET /.well-known/oauth-authorization-server
GET /authorize?client_id=...&redirect_uri=...
POST /token
```

Server delegates user identity to GitHub / Google / your IdP. The OAuth `sub` becomes the credential storage key.

## What about local mode?

`stdio` and `local-relay` modes are single-user by design. No `sub` involved. Don't share `config.enc` across machines.

## Read on

- [Modes overview](/get-started/modes-overview/) — pick the right mode
- [Multi-user pattern](/reference/multi-user-pattern/) — implementation details
