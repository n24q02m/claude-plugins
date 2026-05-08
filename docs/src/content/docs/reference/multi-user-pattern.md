---
title: Multi-user pattern
description: PUBLIC_URL + per-JWT-sub credential storage recipe.
---

Multi-user is a deployment property of `remote-relay` and `remote-oauth` modes. One self-hosted server serves N users; each user's credentials are stored under a key derived from their JWT subject (`sub`).

## Required components

1. **JWT issuer** — anything that produces signed JWTs your client can include in the `Authorization: Bearer <token>` header. Options:
   - Your own OAuth/OIDC provider (Auth0, Authentik, Dex, Keycloak)
   - The MCP server itself in `remote-oauth` mode (it doubles as an AS)
   - GitHub Actions OIDC tokens (workflow-scoped, useful for CI)

2. **PUBLIC_URL env** — the externally-reachable URL of your deployment. Used by the relay form to construct `redirect_url`s and by `oauth-authorization-server` metadata.

3. **JWT public key** — passed via `JWT_PUBLIC_KEY_PEM` or `JWT_JWKS_URL` env. Server verifies every request's JWT against this.

4. **Storage backend** — by default a SQLite file on disk. For HA, point `STORAGE_URL` to Postgres, Redis, or any backend listed in the mcp-core docs.

## Storage key derivation

```
storage_key = "<server-name>:<sub>"
```

Example:

```
wet-mcp:n24q02m@example.com           -> bundle A
wet-mcp:teammate@example.com          -> bundle B
mnemo-mcp:n24q02m@example.com         -> bundle C
```

Same `sub`, different servers → different bundles. Servers never read each others' bundles.

## What's in a bundle

Encrypted blob containing the credential payload submitted via the relay form. AES-256-GCM, key derived from `KEYRING_SECRET` (env-injected) + per-bundle nonce.

Plus metadata (cleartext): created-at, last-rotated-at, expires-at, version. Used for cache invalidation when an underlying upstream rotates keys.

## Deployment example

```yaml
# docker-compose.yml
services:
  wet-mcp:
    image: ghcr.io/n24q02m/wet-mcp:latest
    environment:
      MCP_TRANSPORT: http
      PUBLIC_URL: https://wet-mcp.team.example
      JWT_JWKS_URL: https://auth.team.example/.well-known/jwks.json
      KEYRING_SECRET_FILE: /run/secrets/wet_keyring
    secrets:
      - wet_keyring
    volumes:
      - wet-data:/var/lib/wet-mcp
    restart: unless-stopped
volumes:
  wet-data:
secrets:
  wet_keyring:
    file: ./secrets/wet_keyring.txt
```

## OAuth-AS mode (remote-oauth)

Server exposes:

- `GET /.well-known/oauth-authorization-server`
- `POST /register` — Dynamic Client Registration (DCR) per RFC 7591
- `GET /authorize` — same form as relay, plus OAuth code exchange wrapper
- `POST /token` — exchange code for JWT

Identity (the `sub`) is delegated to an upstream IdP — usually GitHub for OSS deploys. Server signs its own JWTs after delegated auth.

## Anti-patterns

- Shared `config.enc` (single-user storage) in `remote-relay` mode → first user's creds get overwritten by second user's. Server MUST refuse to start if it can't verify per-sub storage is wired. (`feedback_remote_relay_multi_user_enforcement.md`).
- Passing creds in URL query string (`?token=xxx`) → leaks via referer headers + access logs.
- Not rotating `KEYRING_SECRET` on team-member offboarding → ex-team-member can decrypt past bundles if they exfiltrated the secret.

## Read more

- [Modes overview](/get-started/modes-overview/)
- [Relay flow](/reference/relay-flow/)
- [`mcp-core` foundation](/servers/mcp-core/architecture/)
