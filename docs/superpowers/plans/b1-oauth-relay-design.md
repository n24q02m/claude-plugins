# B1: OAuth 2.1 Wrapper for Relay

**Status**: Design complete
**Scope**: mcp-relay-core + all 6 relay servers

## Problem

MCP HTTP transport (claude.ai, remote clients) only supports OAuth 2.1 or no-auth.
Currently only email-mcp and notion-mcp have their own OAuth implementations.
The 4 Python servers (wet, mnemo, crg, telegram) only support stdio with relay for credential setup.

## Design

### Architecture: Relay as OAuth Authorization Server

```
MCP Client (claude.ai)
    |
    | 1. GET /.well-known/oauth-authorization-server
    | 2. POST /register (DCR)
    | 3. GET /authorize (redirect to relay form)
    | 4. User enters credentials on relay form
    | 5. POST /token (exchange code for access token)
    | 6. MCP requests with Bearer token
    |
    v
Relay Server (mcp-relay-core)
    |
    | - Stores per-user credentials (encrypted)
    | - Issues access tokens (JWT or opaque)
    | - Proxies MCP requests to stdio server
    |
    v
MCP Server (stdio mode, unchanged)
```

### Key Components

#### 1. OAuth Metadata Endpoint
```
GET /.well-known/oauth-authorization-server
{
  "issuer": "https://{server}.n24q02m.com",
  "authorization_endpoint": "https://{server}.n24q02m.com/authorize",
  "token_endpoint": "https://{server}.n24q02m.com/token",
  "registration_endpoint": "https://{server}.n24q02m.com/register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code"],
  "code_challenge_methods_supported": ["S256"]
}
```

#### 2. DCR (Dynamic Client Registration)
Reuse StatelessClientStore pattern from email/notion:
- HMAC-SHA256 based, no database needed
- Client ID = HMAC(server_secret, registration_data)
- Stateless verification on each request

#### 3. Authorization Flow
1. Client redirects user to `/authorize?client_id=...&code_challenge=...&state=...`
2. Relay shows credential form (same UI as current relay page)
3. User enters credentials, submits
4. Relay encrypts + stores credentials per-user
5. Relay redirects back with `?code=...&state=...`

#### 4. Token Exchange
1. Client sends `POST /token` with auth code + code_verifier
2. Relay verifies PKCE
3. Relay issues access token (opaque, stored in memory with TTL)
4. Token maps to user's encrypted credential set

#### 5. MCP Request Proxying
1. Client sends MCP request with `Authorization: Bearer {token}`
2. Relay looks up token -> user credentials
3. Relay injects credentials as env vars
4. Relay forwards request to stdio MCP server
5. Returns response to client

### Per-User Credential Storage

Reuse per-user-credential-store.ts pattern from email:
- AES-256-GCM encryption at rest
- Key derived from server secret + user ID
- Stored in `~/.mcp-relay/{server}/{user_id}.enc`

### Session Isolation

- Each user gets their own credential set
- Access tokens are scoped to individual users
- User A cannot access User B's data
- Token TTL: 1 hour, refresh via re-auth

### Backward Compatibility

- Stdio relay continues working unchanged
- HTTP mode is opt-in via `TRANSPORT_MODE=http`
- Existing credential-state.py patterns work for both modes
- Servers don't need code changes (relay handles auth)

## Implementation Plan (B2)

### Phase 1: Core OAuth in relay-server
1. Add OAuth metadata endpoint
2. Add DCR endpoint (stateless HMAC)
3. Add authorization endpoint (reuse relay form UI)
4. Add token endpoint (PKCE verification)
5. Add per-user credential storage
6. Add MCP request proxy with credential injection

### Phase 2: Integration
1. Deploy on oci-vm-prod behind Caddy
2. Test with telegram-mcp (simplest: bot token only)
3. Test with email-mcp (complex: multi-account + Outlook OAuth)
4. Verify multi-user isolation

### Phase 3: Documentation
1. Update relay-core README
2. Add HTTP setup guide for each server
3. Update MCP Registry listings

## Security Considerations

- All credentials encrypted at rest (AES-256-GCM)
- PKCE S256 mandatory (no plain)
- Access tokens opaque, server-side only
- Rate limiting on auth endpoints (20 req/min)
- CORS restricted to known origins
- Session binding: token tied to client_id
