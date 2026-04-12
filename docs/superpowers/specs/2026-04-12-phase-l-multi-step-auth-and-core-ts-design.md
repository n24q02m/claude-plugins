# Phase L — Multi-step Auth, core-ts Parity, Delegated OAuth & 4-Repo Integration

**Date**: 2026-04-12
**Status**: Draft for review
**Predecessor**: Phase K (local OAuth AS + transport migration, 3/7 repos DONE)
**Spec reference**: `2026-04-10-mcp-core-unified-transport-design.md` (Objectives O14, O15, O16)
**Scope**: mcp-core (core-py + core-ts) + better-telegram-mcp + better-email-mcp + better-notion-mcp + better-godot-mcp

---

## 1. Context

### 1.1 Phase K completed (3/7 repos)

| Repo | Commit | Status |
|------|--------|--------|
| wet-mcp | `7093cb9` | DONE — mcp-core OAuth + GDrive device code, E2E PASS |
| mnemo-mcp | `4717c7c` | DONE — same pattern, E2E PASS |
| better-code-review-graph | `0bf7084` | DONE — mcp-core OAuth, no GDrive, E2E PASS |

### 1.2 Remaining 4 repos — gaps identified

| Repo | Current state | Gap |
|------|--------------|-----|
| **better-telegram-mcp** (`b14078d`) | Uses mcp-core `run_local_server` + `save_credentials`. Bot mode complete. User mode returns info "run --stdio" — **broken** | mcp-core credential form lacks multi-step auth (OTP + 2FA) |
| **better-email-mcp** (`ad862ba`) | Own `oauth-server.ts` (380 lines Express). Uses mcp-core relay client + JWT + user store | No core-ts equivalent of `create_local_oauth_app` / `run_local_server` / credential form |
| **better-notion-mcp** (`fb99551`) | Own `http.ts` (300 lines Express) + `notion-oauth-provider.ts` (150+ lines) + `stateless-client-store.ts` (79 lines) | Same core-ts gap. Custom delegated OAuth needs consolidation |
| **better-godot-mcp** (`a7c5fca`) | Own `http.ts` (128 lines bare Node.js `http`). No auth | Should use core-ts for consistency |

### 1.3 User requirements (locked in this session)

1. Multi-step auth: inline dynamic form (same page, no reload)
2. core-ts: bare Node.js `http` module, zero framework dependency (Express is app-level, not library-level)
3. DelegatedOAuthProvider: unified abstraction for device code (GDrive, Outlook) + redirect (Notion, Grafana, GitHub future)
4. Email: test IMAP connection before marking complete
5. ALL 7 repos must use mcp-core (no exceptions, including godot)
6. E2E = interactive, browser, real credentials, ALL tools/actions

---

## 2. Architectural decisions

### 2.1 Decision: Multi-step auth protocol in mcp-core credential form

**Extend existing `next_step` mechanism** to support chained input collection on a single page.

**Current `next_step` types** (already implemented):
- `oauth_device_code` — form shows verification URL + user code, polls `/setup-status`
- `info` — form shows static message

**New `next_step` types**:
- `otp_required` — form hides initial fields, renders a text input, POSTs to `/otp`
- `password_required` — form renders a password input, POSTs to `/otp`
- `error` — form shows error message, allows retry on same input

**New endpoint**: `POST /otp` in `local_oauth_app.py` receives step input, invokes `on_step_submitted` callback, returns next step or completion.

**New callback**: `on_step_submitted(step_data: dict[str, str]) -> dict | None` added to `create_local_oauth_app` parameters.

**Form JS state machine** (all transitions on same page, no reload):

```
INITIAL (credential fields visible)
  → submit credentials
  → response.next_step?
    ├─ null → COMPLETE ("Setup complete!")
    ├─ type: "info" → COMPLETE (show message)
    ├─ type: "oauth_device_code" → DEVICE_CODE_POLLING (show URL + code, poll /setup-status)
    │   └─ /setup-status.gdrive === "complete" → COMPLETE
    ├─ type: "otp_required" → STEP_INPUT (hide fields, show input)
    │   → user enters value, POST /otp
    │   → response.next_step?
    │     ├─ null → COMPLETE
    │     ├─ type: "password_required" → STEP_INPUT (replace input with password field)
    │     ├─ type: "error" → STEP_INPUT (show error, keep same input for retry)
    │     └─ type: "otp_required" → STEP_INPUT (new OTP, e.g. code expired and resent)
    └─ type: "password_required" → STEP_INPUT (same as otp_required but password type)
```

**Rationale**: Minimal protocol extension. Reuses existing form infrastructure. No new pages, no URL state management. The `/otp` endpoint name is generic enough for any step input (OTP, 2FA password, verification code).

### 2.2 Decision: core-ts uses bare Node.js `http` module

**core-ts provides framework-agnostic request handlers**, not Express apps.

**Primary export type**:
```typescript
type RequestHandler = (req: IncomingMessage, res: ServerResponse) => void | Promise<void>;
```

**Internal routing**: ~40-line utility matching `req.method` + `req.url` pathname. Not exported — implementation detail.

**Rationale**:
- core-py uses Starlette (lightweight ASGI standard). Equivalent in Node.js is the built-in `http` module, not Express.
- core-ts is a **library**, not an application. Libraries minimize dependencies. Express adds ~60 transitive deps.
- MCP SDK's `StreamableHTTPServerTransport` works with `(req, res)` directly — no framework needed.
- better-godot-mcp already uses this pattern successfully (128 lines, 682 tests pass).
- Consumers can wrap the handler in Express/Fastify/Hono if they choose — core doesn't force a framework.

### 2.3 Decision: DelegatedOAuthProvider — unified abstraction

**One abstraction for two OAuth delegation flows**: device code (RFC 8628) and redirect (RFC 6749).

**Consumers**:

| Flow | Current | Future |
|------|---------|--------|
| Device code | GDrive (wet, mnemo), Outlook (email) | — |
| Redirect | Notion | Grafana, GitHub |

**Both flows share**: upstream token exchange, JWT wrapping for own clients, credential storage via callback. They differ only in user interaction.

**API** (core-py):
```python
def create_delegated_oauth_app(
    *,
    server_name: str,
    flow: Literal["device_code", "redirect"],
    upstream: UpstreamOAuthConfig,
    on_token_received: Callable[[dict[str, str]], None | Awaitable[None]],
    jwt_issuer: JWTIssuer | None = None,
) -> tuple[Starlette, JWTIssuer]:
```

**API** (core-ts):
```typescript
function createDelegatedOAuthApp(options: {
  serverName: string;
  flow: "device_code" | "redirect";
  upstream: UpstreamOAuthConfig;
  onTokenReceived: (tokens: OAuthTokens) => void | Promise<void>;
  jwtIssuer?: JWTIssuer;
}): { handler: RequestHandler; jwtIssuer: JWTIssuer };
```

**UpstreamOAuthConfig**:
```typescript
interface UpstreamOAuthConfig {
  // Common
  tokenUrl: string;
  clientId: string;
  clientSecret?: string;
  scopes: string[];
  // Redirect flow
  authorizeUrl?: string;       // required if flow === "redirect"
  callbackPath?: string;       // default: "/callback"
  // Device code flow
  deviceAuthUrl?: string;      // required if flow === "device_code"
  pollIntervalMs?: number;     // default: 5000
}
```

**Device code flow** (server-side):
1. Consumer's `on_credentials_saved` triggers device code request to `upstream.deviceAuthUrl`
2. Returns `next_step: {type: "oauth_device_code", verification_url, user_code}`
3. Background task polls `upstream.tokenUrl` until token granted
4. `onTokenReceived(tokens)` → `mark_setup_complete()`

**Redirect flow** (server-side):
1. `GET /authorize` → redirect to `upstream.authorizeUrl?client_id=...&redirect_uri=.../callback&scope=...&state=...`
2. Upstream authorizes → redirect to `GET /callback?code=...&state=...`
3. Exchange code at `upstream.tokenUrl` → receive tokens
4. `onTokenReceived(tokens)` → issue own auth code → redirect client

**Rationale**: 5 consumers (current + planned) justify a shared abstraction. Server-side token exchange, JWT wrapping, and client auth code flow are identical across all providers.

### 2.4 Decision: Mode composition matrix

Each MCP server selects its auth configuration at startup:

| Mode | Factory | Use case |
|------|---------|----------|
| **Local self-hosted AS** | `createLocalOAuthApp(relaySchema, onCredentialsSaved, onStepSubmitted)` | User fills credential form. wet, mnemo, crg, telegram, email (Gmail), notion (local) |
| **Local self-hosted AS + device code** | Local AS + device code in `onCredentialsSaved` callback | Credential form + GDrive/Outlook device code. wet, mnemo, email (Outlook) |
| **Remote delegated redirect** | `createDelegatedOAuthApp(flow: "redirect", upstream)` | Multi-user, upstream OAuth. notion (remote), grafana, github (future) |
| **No auth** | `runLocalServer(serverFactory, {})` — no relaySchema | godot |

Servers with both local and remote modes (notion) select at startup based on env var `MCP_CORE_MODE`.

---

## 3. Integration design per repo

### 3.1 better-telegram-mcp

**Changes**:
- `server.py`: `run_http()` passes `on_step_submitted` callback to `run_local_server`
- `credential_state.py`:
  - `save_credentials()`: if user mode (phone, no bot token) → `backend.connect()` + `backend.send_code(phone)` → return `{type: "otp_required", text: "Enter OTP from Telegram", field: "otp_code", input_type: "text"}`
  - `on_step_submitted()`: if `otp_code` → `backend.sign_in(phone, code)` → if needs 2FA → return `{type: "password_required", text: "Enter 2FA password", field: "password", input_type: "password"}` → else return `None` (complete). If `password` → `backend.sign_in(phone, code, password)` → return `None`
- `relay_setup.py`: remove `_relay_telethon_auth()` and relay messaging OTP flow (replaced by `/otp` endpoint)
- Bot mode: unchanged (save token → complete immediately)

**State management**: `UserBackend` instance and phone/otp_code held in module-level state during multi-step flow. Cleaned up on complete or timeout.

**Timeout**: 300 seconds for OTP entry (matching current relay behavior). `/otp` endpoint checks elapsed time.

### 3.2 better-email-mcp

**Changes**:
- Delete: `src/transports/oauth-server.ts` (380 lines) — replaced entirely by core-ts
- `init-server.ts`: HTTP mode imports `runLocalServer` from `@n24q02m/mcp-core`
- `credential-state.ts` (new or refactored):
  - `onCredentialsSaved()`: parse `EMAIL_CREDENTIALS` (format: `user@gmail.com:app-password`) → test IMAP connection → if pass, return `None` (complete) → if fail, return `{type: "error", text: "IMAP connection failed: <reason>"}`
  - Outlook: if email domain is outlook/hotmail/live → trigger device code flow → return `{type: "oauth_device_code", ...}`
- `relay-schema.ts`: unchanged (single field `EMAIL_CREDENTIALS`)

**IMAP connection test**: attempt `IMAP.connect()` + `login()` + `logout()` with 10-second timeout. On success → complete. On auth failure → error in form. On timeout → error with retry option.

### 3.3 better-notion-mcp

**Changes**:
- Delete: `src/transports/http.ts` (300 lines Express)
- Delete: `src/auth/notion-oauth-provider.ts` (150+ lines) — replaced by core-ts `DelegatedOAuthProvider`
- Delete: `src/auth/stateless-client-store.ts` (79 lines) — DCR handled by core-ts
- `init-server.ts`:
  - Local mode (`MCP_CORE_MODE !== "remote"`): `runLocalServer` with `relaySchema` (single field: `NOTION_TOKEN`, paste integration token → complete)
  - Remote mode: `createDelegatedOAuthApp(flow: "redirect", upstream: notionOAuth)` + `runLocalServer` with delegated handler
- `relay-schema.ts`: unchanged (single field `NOTION_TOKEN`)

**Local mode**: simplest — paste Notion integration token → `onCredentialsSaved` saves → complete. No multi-step, no device code.

**Remote mode**: `createDelegatedOAuthApp` handles full Notion OAuth redirect flow. `onTokenReceived` creates `Client({ auth: access_token })`.

### 3.4 better-godot-mcp

**Changes**:
- Delete: `src/transports/http.ts` (128 lines) — replaced by core-ts `runLocalServer`
- `init-server.ts`: HTTP mode calls `runLocalServer(createGodotServer, { serverName: "better-godot-mcp" })` — no `relaySchema` (no auth)
- No credential handling, no OAuth

**Simplest migration**: just swap custom HTTP setup for `runLocalServer` one-liner.

---

## 4. core-ts module inventory

### 4.1 New modules

| Module | File | Responsibility |
|--------|------|----------------|
| `auth/credential-form` | `src/auth/credential-form.ts` | Render HTML form. Same visual design as core-py. Handles all `next_step` types in embedded JS. |
| `auth/local-oauth-app` | `src/auth/local-oauth-app.ts` | Self-hosted OAuth 2.1 AS. Routes: `/authorize` (GET/POST), `/token` (POST), `/otp` (POST), `/setup-status` (GET), `/.well-known/*` (GET). Returns `RequestHandler`. |
| `auth/well-known` | `src/auth/well-known.ts` | RFC 8414 + RFC 9728 metadata generators. Pure functions. |
| `auth/delegated-oauth-app` | `src/auth/delegated-oauth-app.ts` | Delegated OAuth provider. Device code + redirect flows. Returns `RequestHandler`. |
| `transport/local-server` | `src/transport/local-server.ts` | `runLocalServer()` — compose auth handler + MCP `StreamableHTTPServerTransport` + `http.createServer()` + bind `127.0.0.1`. |
| Internal: `auth/router` | `src/auth/router.ts` | Minimal path+method router. Not exported. |

### 4.2 Existing modules (unchanged)

| Module | Status |
|--------|--------|
| `crypto/*` | Unchanged — AES, ECDH, KDF |
| `oauth/jwt-issuer` | Unchanged — used by local + delegated OAuth apps |
| `oauth/provider` | Unchanged |
| `oauth/user-store` | Unchanged — used by remote multi-user mode |
| `relay/*` | Unchanged — relay client for backward compat |
| `storage/*` | Unchanged — config file, encryption, machine-id |
| `transport/streamable-http` | Unchanged — MCP transport base |
| `transport/oauth-middleware` | Unchanged — Bearer token verification middleware |

### 4.3 core-py additions

| Module | File | Responsibility |
|--------|------|----------------|
| `auth/delegated_oauth_app` | `src/mcp_core/auth/delegated_oauth_app.py` | Delegated OAuth provider (device code + redirect). Starlette app. |

Existing `auth/local_oauth_app.py` extended with `/otp` endpoint + `on_step_submitted` callback.

Existing `auth/credential_form.py` extended with `otp_required` + `password_required` + `error` handling in form JS.

---

## 5. Security considerations

### 5.1 Multi-step auth

- OTP codes are short-lived (Telegram OTP expires in ~5 minutes). `/otp` endpoint enforces 300-second timeout from initial `save_credentials` call.
- `on_step_submitted` callback runs server-side. OTP/password values never stored — passed directly to Telethon `sign_in()` and discarded.
- Form disables input after submission to prevent double-submit.
- Rate limiting: 5 attempts per session. After 5 failures, nonce invalidated.

### 5.2 Delegated OAuth

- Redirect flow: `state` parameter tied to PKCE session, verified on callback. Prevents CSRF.
- Device code flow: polling interval respects upstream `interval` field (RFC 8628 Section 3.5). No faster than 5 seconds.
- Tokens from upstream stored encrypted in `config.enc` (local mode) or `SqliteUserStore` (remote mode).
- Client secrets for upstream providers sourced from env vars, never hardcoded.

### 5.3 IMAP connection test (email)

- Test connection uses TLS by default (`IMAPS` port 993).
- Credentials tested server-side only — never exposed to form JS.
- Connection test has 10-second timeout to prevent hanging.
- On test failure, credentials are NOT saved — user must fix and resubmit.

### 5.4 core-ts handler security

- `127.0.0.1` bind only for local mode (same as core-py).
- `Origin` header validation: accept `http://127.0.0.1:*` and `http://localhost:*`.
- `Host` header validation: reject anything other than `127.0.0.1`, `localhost`, `::1`.
- All dynamic HTML content escaped via `escapeHtml()` utility.

---

## 6. Testing strategy

### 6.1 Unit tests

- core-py: `tests/auth/test_local_oauth_app.py` — add `/otp` endpoint tests (multi-step flow)
- core-py: `tests/auth/test_delegated_oauth_app.py` — device code + redirect flow mocks
- core-ts: `tests/auth/credential-form.test.ts` — HTML output snapshot, XSS escaping
- core-ts: `tests/auth/local-oauth-app.test.ts` — full OAuth flow via `supertest` or raw `http.request`
- core-ts: `tests/auth/delegated-oauth-app.test.ts` — device code polling, redirect flow
- core-ts: `tests/transport/local-server.test.ts` — server lifecycle, port binding

### 6.2 Integration tests

- Telegram: `on_step_submitted` chain — phone → OTP → (2FA) → complete, with Telethon mock
- Email: `onCredentialsSaved` → IMAP test → complete/error, with IMAP server mock
- Notion: local mode paste token → complete. Remote mode redirect → callback → complete.
- Godot: HTTP server starts, `/mcp` responds, no auth required.

### 6.3 E2E tests (interactive, real credentials)

Per repo, following existing E2E protocol:
1. Clean state: delete `config.enc`, unset env vars
2. Start server from source (`uv run` / `bun run`)
3. Browser opens credential form
4. User enters real credentials
5. All tools tested with real data
6. Restart persistence verified

---

## 7. Execution order

### Track 1: Python (mcp-core + telegram)

| Step | Deliverable | Dependency |
|------|-------------|-----------|
| L1 | mcp-core: multi-step auth (`/otp` endpoint + form JS + `on_step_submitted`) | None |
| L2 | better-telegram-mcp: integrate multi-step auth, remove relay OTP flow | L1 |
| L2-E2E | Telegram E2E: bot mode + user mode (OTP + 2FA) with real credentials | L2 |

### Track 2: TypeScript (core-ts + 3 repos)

| Step | Deliverable | Dependency |
|------|-------------|-----------|
| L3 | core-ts: `credential-form` + `local-oauth-app` + `well-known` + `router` + `local-server` | None |
| L4 | better-godot-mcp: replace custom http.ts with core-ts `runLocalServer` | L3 |
| L4-E2E | Godot E2E: HTTP transport, all tools | L4 |
| L5 | core-ts: `delegated-oauth-app` (device code + redirect) | L3 |
| L5-core-py | core-py: `delegated_oauth_app` (device code + redirect) | None |
| L6 | better-notion-mcp: local mode (core-ts local OAuth) + remote mode (core-ts delegated redirect) | L3, L5 |
| L6-E2E | Notion E2E: local token paste + remote OAuth redirect | L6 |
| L7 | better-email-mcp: replace oauth-server.ts with core-ts local OAuth + IMAP test + Outlook device code | L3, L5 |
| L7-E2E | Email E2E: Gmail app password (IMAP test) + Outlook device code | L7 |

### Final gate

| Step | Deliverable |
|------|-------------|
| L8 | Full E2E re-test ALL 7 repos: clean state, real credentials, all tools/actions, restart persistence |

Track 1 and Track 2 can run in parallel (Python and TypeScript, no shared code).

---

## 8. Exit criteria

- [ ] mcp-core core-py: `/otp` endpoint + `on_step_submitted` callback + form JS handles `otp_required` / `password_required` / `error`
- [ ] mcp-core core-py: `DelegatedOAuthProvider` for device code + redirect
- [ ] mcp-core core-ts: `createLocalOAuthApp` + `runLocalServer` + `renderCredentialForm` + well-known metadata
- [ ] mcp-core core-ts: `createDelegatedOAuthApp` for device code + redirect
- [ ] core-ts: zero framework dependency (bare Node.js `http`)
- [ ] better-telegram-mcp: user mode OTP + 2FA via `/otp` endpoint, bot mode unchanged
- [ ] better-email-mcp: core-ts local OAuth, IMAP connection test, Outlook device code
- [ ] better-notion-mcp: core-ts local OAuth (paste token) + core-ts delegated redirect (remote Notion OAuth)
- [ ] better-godot-mcp: core-ts `runLocalServer` (no auth)
- [ ] All 4 repos: delete custom transport code (Express, Node.js http self-implemented)
- [ ] All existing unit tests pass across all repos
- [ ] E2E: all 7 repos tested with real credentials, all tools/actions, restart persistence

---

## 9. References

- Phase K spec: `specs/2026-04-10-mcp-core-unified-transport-design.md`
- Phase K plan: `plans/2026-04-12-phase-k-local-oauth-transport-migration.md`
- MCP Streamable HTTP 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- OAuth 2.1 (RFC 9470), Device Authorization Grant (RFC 8628)
- OAuth AS Metadata (RFC 8414), Protected Resource Metadata (RFC 9728)
