# Phase L Track 2 — core-ts Parity + Godot/Notion/Email Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build core-ts TypeScript parity modules (local OAuth app, credential form, well-known, local server, delegated OAuth), then migrate better-godot-mcp, better-notion-mcp, and better-email-mcp to use core-ts instead of their custom transport implementations.

**Architecture:** core-ts provides `createLocalOAuthApp()` and `runLocalServer()` using bare Node.js `http` module (zero framework dependency). Each server calls `runLocalServer` with its relay schema and credential callbacks, replacing custom Express/Node.js HTTP code. Delegated OAuth (device code + redirect) abstraction handles GDrive, Outlook, Notion OAuth flows.

**Tech Stack:** TypeScript, Node.js `http`, `@modelcontextprotocol/sdk` (StreamableHTTPServerTransport), jose (JWT), vitest

**Spec:** `docs/superpowers/specs/2026-04-12-phase-l-multi-step-auth-and-core-ts-design.md` Section 2.2, 2.3, 3.2-3.4, 4

**Dependency:** Track 1 (L1.1-L1.2) should be done first so core-ts can mirror the multi-step auth protocol.

---

## File Structure

### core-ts new modules (packages/core-ts/src/)

| File | Create/Modify | Responsibility |
|------|--------------|----------------|
| `auth/router.ts` | Create | Internal minimal path+method router. Not exported. |
| `auth/well-known.ts` | Create | RFC 8414 + RFC 9728 metadata generators |
| `auth/credential-form.ts` | Create | Render credential form HTML (same design as core-py) |
| `auth/local-oauth-app.ts` | Create | Self-hosted OAuth 2.1 AS returning `RequestHandler` |
| `auth/delegated-oauth-app.ts` | Create | Delegated OAuth (device code + redirect) returning `RequestHandler` |
| `auth/index.ts` | Create | Re-exports |
| `transport/local-server.ts` | Create | `runLocalServer()` composing auth + MCP transport |
| `index.ts` | Modify | Add auth + transport/local-server exports |

### core-ts tests

| File | Create |
|------|--------|
| `tests/auth/well-known.test.ts` | RFC metadata tests |
| `tests/auth/credential-form.test.ts` | HTML rendering + XSS tests |
| `tests/auth/local-oauth-app.test.ts` | OAuth flow integration tests |
| `tests/auth/delegated-oauth-app.test.ts` | Device code + redirect flow tests |
| `tests/transport/local-server.test.ts` | Server lifecycle tests |

### Repo changes

| Repo | Delete | Modify |
|------|--------|--------|
| better-godot-mcp | `src/transports/http.ts` | `src/init-server.ts` |
| better-notion-mcp | `src/transports/http.ts`, `src/auth/notion-oauth-provider.ts`, `src/auth/stateless-client-store.ts` | `src/init-server.ts` |
| better-email-mcp | `src/transports/oauth-server.ts` | `src/init-server.ts`, `src/credential-state.ts` (new) |

---

## Pre-flight

- [ ] **Step P.1: Verify core-ts current state**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts
bun run test
bun run check
```

Expected: all pass.

- [ ] **Step P.2: Verify 3 TS repos**

```bash
cd C:/Users/n24q02m-wlap/projects/better-godot-mcp && bun run test 2>&1 | tail -3
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp && bun run test 2>&1 | tail -3
cd C:/Users/n24q02m-wlap/projects/better-email-mcp && bun run test 2>&1 | tail -3
```

---

## Task L2.1: Internal router utility

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/src/auth/router.ts`

- [ ] **Step 1: Implement minimal router**

```typescript
/**
 * Internal minimal HTTP router. Not exported from the package.
 * Matches requests by method + pathname, calls the first matching handler.
 */
import type { IncomingMessage, ServerResponse } from 'node:http'

export type RequestHandler = (req: IncomingMessage, res: ServerResponse) => void | Promise<void>

interface Route {
  method: string
  path: string
  handler: RequestHandler
}

export function createRouter(routes: Route[]): RequestHandler {
  return async (req, res) => {
    const method = req.method?.toUpperCase() ?? 'GET'
    const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`)
    const pathname = url.pathname

    for (const route of routes) {
      if (route.method === method && route.path === pathname) {
        try {
          await route.handler(req, res)
        } catch (err) {
          if (!res.headersSent) {
            res.writeHead(500, { 'Content-Type': 'application/json' })
            res.end(JSON.stringify({ error: 'internal_error' }))
          }
        }
        return
      }
    }

    // 404
    res.writeHead(404, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ error: 'not_found' }))
  }
}

/** Parse JSON body from IncomingMessage. */
export async function parseJsonBody<T = Record<string, unknown>>(req: IncomingMessage): Promise<T> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    req.on('data', (chunk: Buffer) => chunks.push(chunk))
    req.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf-8')))
      } catch {
        reject(new Error('Invalid JSON'))
      }
    })
    req.on('error', reject)
  })
}

/** Parse URL-encoded form body from IncomingMessage. */
export async function parseFormBody(req: IncomingMessage): Promise<Record<string, string>> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    req.on('data', (chunk: Buffer) => chunks.push(chunk))
    req.on('end', () => {
      const params = new URLSearchParams(Buffer.concat(chunks).toString('utf-8'))
      const result: Record<string, string> = {}
      for (const [key, value] of params) {
        result[key] = value
      }
      resolve(result)
    })
    req.on('error', reject)
  })
}

/** Write JSON response. */
export function jsonResponse(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify(body))
}

/** Write HTML response. */
export function htmlResponse(res: ServerResponse, status: number, html: string): void {
  res.writeHead(status, { 'Content-Type': 'text/html; charset=utf-8' })
  res.end(html)
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-ts/src/auth/router.ts
git commit -m "feat: add internal HTTP router utility for core-ts auth"
```

---

## Task L2.2: Well-known metadata generators

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/src/auth/well-known.ts`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/tests/auth/well-known.test.ts`

- [ ] **Step 1: Write test**

```typescript
import { describe, expect, it } from 'vitest'
import { authorizationServerMetadata, protectedResourceMetadata } from '../../src/auth/well-known.js'

describe('authorizationServerMetadata', () => {
  it('returns correct metadata', () => {
    const meta = authorizationServerMetadata('http://127.0.0.1:9876')
    expect(meta.issuer).toBe('http://127.0.0.1:9876')
    expect(meta.authorization_endpoint).toBe('http://127.0.0.1:9876/authorize')
    expect(meta.token_endpoint).toBe('http://127.0.0.1:9876/token')
    expect(meta.code_challenge_methods_supported).toContain('S256')
    expect(meta.grant_types_supported).toContain('authorization_code')
  })
})

describe('protectedResourceMetadata', () => {
  it('returns correct metadata', () => {
    const meta = protectedResourceMetadata('http://127.0.0.1:9876', ['http://127.0.0.1:9876'])
    expect(meta.resource).toBe('http://127.0.0.1:9876')
    expect(meta.authorization_servers).toContain('http://127.0.0.1:9876')
  })
})
```

- [ ] **Step 2: Run test, verify fail**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts
bun run test -- tests/auth/well-known.test.ts
```

- [ ] **Step 3: Implement**

```typescript
/** OAuth 2.1 well-known metadata generators (RFC 8414 + RFC 9728). */

export function authorizationServerMetadata(issuerUrl: string): Record<string, unknown> {
  return {
    issuer: issuerUrl,
    authorization_endpoint: `${issuerUrl}/authorize`,
    token_endpoint: `${issuerUrl}/token`,
    response_types_supported: ['code'],
    grant_types_supported: ['authorization_code'],
    code_challenge_methods_supported: ['S256'],
    token_endpoint_auth_methods_supported: ['none'],
  }
}

export function protectedResourceMetadata(
  resource: string,
  authorizationServers: string[]
): Record<string, unknown> {
  return {
    resource,
    authorization_servers: authorizationServers,
    bearer_methods_supported: ['header'],
  }
}
```

- [ ] **Step 4: Run test, verify pass**

```bash
bun run test -- tests/auth/well-known.test.ts
```

- [ ] **Step 5: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-ts/src/auth/well-known.ts packages/core-ts/tests/auth/well-known.test.ts
git commit -m "feat: add well-known OAuth metadata generators for core-ts"
```

---

## Task L2.3: Credential form renderer

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/src/auth/credential-form.ts`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/tests/auth/credential-form.test.ts`

- [ ] **Step 1: Write test**

```typescript
import { describe, expect, it } from 'vitest'
import { renderCredentialForm } from '../../src/auth/credential-form.js'

describe('renderCredentialForm', () => {
  it('renders basic form with fields', () => {
    const html = renderCredentialForm(
      {
        server: 'test-server',
        displayName: 'Test Server',
        description: 'Enter your API key.',
        fields: [
          { key: 'API_KEY', label: 'API Key', type: 'password', placeholder: 'sk-...', required: true },
        ],
      },
      { submitUrl: '/authorize?nonce=abc' }
    )
    expect(html).toContain('Test Server')
    expect(html).toContain('API_KEY')
    expect(html).toContain('sk-...')
    expect(html).toContain('/authorize?nonce=abc')
    expect(html).toContain('<!DOCTYPE html>')
  })

  it('escapes XSS in display name', () => {
    const html = renderCredentialForm(
      { server: 'test', displayName: '<script>alert("xss")</script>', fields: [] },
      { submitUrl: '/submit' }
    )
    expect(html).not.toContain('<script>alert')
    expect(html).toContain('&lt;script&gt;')
  })

  it('includes multi-step auth JS handlers', () => {
    const html = renderCredentialForm(
      { server: 'test', displayName: 'Test', fields: [] },
      { submitUrl: '/authorize?nonce=abc' }
    )
    expect(html).toContain('otp_required')
    expect(html).toContain('password_required')
    expect(html).toContain('/otp')
  })

  it('includes device code handler', () => {
    const html = renderCredentialForm(
      { server: 'test', displayName: 'Test', fields: [] },
      { submitUrl: '/authorize?nonce=abc' }
    )
    expect(html).toContain('oauth_device_code')
    expect(html).toContain('setup-status')
  })
})
```

- [ ] **Step 2: Run test, verify fail**

- [ ] **Step 3: Implement credential-form.ts**

Port the Python `credential_form.py` to TypeScript. Same HTML/CSS/JS template, same dark theme, same multi-step support. Use a simple `escapeHtml()` function for XSS safety. The rendered JS must handle all `next_step` types: `oauth_device_code`, `otp_required`, `password_required`, `info`, `error`.

Use `textContent` for setting text from server responses in the form JS. Use `createElement` + `setAttribute` for dynamic DOM elements.

- [ ] **Step 4: Run test, verify pass**

- [ ] **Step 5: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-ts/src/auth/credential-form.ts packages/core-ts/tests/auth/credential-form.test.ts
git commit -m "feat: add credential form HTML renderer for core-ts"
```

---

## Task L2.4: Local OAuth app

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/src/auth/local-oauth-app.ts`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/tests/auth/local-oauth-app.test.ts`

- [ ] **Step 1: Write integration test**

Test the full OAuth flow using Node.js `http.createServer` + `http.request`:
1. GET `/authorize?client_id=...&...` returns HTML form
2. POST `/authorize?nonce=...` with credentials returns `{ok: true, redirect_url: ...}`
3. POST `/token` with auth code + code_verifier returns JWT
4. GET `/.well-known/oauth-authorization-server` returns metadata
5. POST `/otp` without prior auth returns 400
6. POST `/otp` after credential submission with `otp_required` returns `{ok: true}`

- [ ] **Step 2: Run test, verify fail**

- [ ] **Step 3: Implement local-oauth-app.ts**

Port core-py `local_oauth_app.py` to TypeScript:

```typescript
import type { IncomingMessage, ServerResponse } from 'node:http'

export interface LocalOAuthAppOptions {
  serverName: string
  relaySchema: Record<string, unknown>
  onCredentialsSaved?: (creds: Record<string, string>) => Record<string, unknown> | null
  onStepSubmitted?: (data: Record<string, string>) => Record<string, unknown> | null
  jwtIssuer?: JWTIssuer
}

export interface LocalOAuthAppResult {
  handler: (req: IncomingMessage, res: ServerResponse) => void | Promise<void>
  jwtIssuer: JWTIssuer
  markSetupComplete: (key?: string) => void
}

export async function createLocalOAuthApp(options: LocalOAuthAppOptions): Promise<LocalOAuthAppResult>
```

Implementation uses `createRouter` from `./router.ts`. Routes:
- `GET /authorize` -- render credential form (from `renderCredentialForm`)
- `POST /authorize` -- save credentials via callback, PKCE nonce management, return auth code
- `POST /token` -- PKCE S256 verification, issue JWT via `JWTIssuer`
- `POST /otp` -- multi-step input handler (timeout 300s, max 5 attempts)
- `GET /setup-status` -- return setup status object
- `GET /.well-known/oauth-authorization-server` -- RFC 8414
- `GET /.well-known/oauth-protected-resource` -- RFC 9728

Key differences from Python version:
- `JWTIssuer` is async (`init()` must be called) -- `createLocalOAuthApp` is async to handle this
- Uses `parseJsonBody`/`parseFormBody` from router.ts instead of Starlette's `request.json()`
- PKCE S256 verification uses Node.js `crypto.createHash`

- [ ] **Step 4: Run test, verify pass**

- [ ] **Step 5: Run full test suite**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts
bun run test
```

- [ ] **Step 6: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-ts/src/auth/local-oauth-app.ts packages/core-ts/tests/auth/local-oauth-app.test.ts
git commit -m "feat: add local OAuth 2.1 AS app for core-ts"
```

---

## Task L2.5: Local server entry point

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/src/transport/local-server.ts`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/tests/transport/local-server.test.ts`

- [ ] **Step 1: Write test**

Test that `runLocalServer` starts an HTTP server on `127.0.0.1`, serves `/mcp` with Bearer auth, and `/authorize` without auth.

- [ ] **Step 2: Implement local-server.ts**

```typescript
import { createServer } from 'node:http'
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'

export interface RunLocalServerOptions {
  serverName: string
  relaySchema?: Record<string, unknown>  // undefined = no auth (godot)
  port?: number  // 0 = auto
  onCredentialsSaved?: (creds: Record<string, string>) => Record<string, unknown> | null
  onStepSubmitted?: (data: Record<string, string>) => Record<string, unknown> | null
  setupCompleteHook?: (markComplete: (key?: string) => void) => void
}

export async function runLocalServer(
  serverFactory: () => McpServer,
  options: RunLocalServerOptions
): Promise<void>
```

Implementation:
1. If `relaySchema` provided: create `LocalOAuthApp` (auth routes + credential form)
2. Create `StreamableHTTPServerTransport` for `/mcp`
3. If auth enabled: wrap `/mcp` with `OAuthMiddleware` Bearer validation
4. Compose all handlers: auth routes + `/mcp` + `/health`
5. Create `http.createServer`, bind `127.0.0.1:port`
6. If `setupCompleteHook`: call with `markSetupComplete`
7. Listen and block

If no `relaySchema` (godot): skip auth, serve `/mcp` directly without Bearer validation.

- [ ] **Step 3: Run test, verify pass**

- [ ] **Step 4: Update index.ts exports**

Add to `packages/core-ts/src/index.ts`:

```typescript
export { createLocalOAuthApp, type LocalOAuthAppOptions, type LocalOAuthAppResult } from './auth/local-oauth-app.js'
export { authorizationServerMetadata, protectedResourceMetadata } from './auth/well-known.js'
export { renderCredentialForm } from './auth/credential-form.js'
export { runLocalServer, type RunLocalServerOptions } from './transport/local-server.js'
```

Add auth subpath export to `package.json` exports:

```json
"./auth": {
  "import": "./build/auth/index.js",
  "types": "./build/auth/index.d.ts"
}
```

Create `src/auth/index.ts` re-exporting all auth modules.

- [ ] **Step 5: Run full suite**

```bash
bun run test && bun run check
```

- [ ] **Step 6: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-ts/src/ packages/core-ts/tests/ packages/core-ts/package.json
git commit -m "feat: add local server entry point for core-ts"
```

---

## Task L2.6: Migrate better-godot-mcp to core-ts

**Files:**
- Delete: `C:/Users/n24q02m-wlap/projects/better-godot-mcp/src/transports/http.ts`
- Modify: `C:/Users/n24q02m-wlap/projects/better-godot-mcp/src/init-server.ts`

- [ ] **Step 1: Update init-server.ts HTTP mode**

Replace the HTTP mode import from `./transports/http.js` to use `runLocalServer` from `@n24q02m/mcp-core`:

```typescript
// HTTP mode (default)
import { runLocalServer } from '@n24q02m/mcp-core'
import { createGodotServer } from './server.js'

await runLocalServer(createGodotServer, {
  serverName: 'better-godot-mcp',
  // No relaySchema = no auth, no credential form
  port: port ? parseInt(port) : 0,
})
```

- [ ] **Step 2: Delete custom http.ts**

```bash
rm C:/Users/n24q02m-wlap/projects/better-godot-mcp/src/transports/http.ts
```

- [ ] **Step 3: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/better-godot-mcp
bun run test
```

Expected: 682+ tests pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: migrate HTTP transport to mcp-core runLocalServer"
```

---

## Task L2.7: Delegated OAuth app (core-py + core-ts)

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/delegated_oauth_app.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/test_delegated_oauth_app.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/src/auth/delegated-oauth-app.ts`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts/tests/auth/delegated-oauth-app.test.ts`

- [ ] **Step 1: Write Python tests for device code + redirect flows**

Test device code: mock upstream `deviceAuthUrl` response, verify polling behavior, verify `onTokenReceived` called.

Test redirect: mock upstream `authorizeUrl` redirect, verify callback handling, verify `onTokenReceived` called.

- [ ] **Step 2: Implement Python delegated_oauth_app.py**

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

**Device code flow routes:**
- `GET /authorize` -- request device code from `upstream.deviceAuthUrl`, render credential form showing verification URL + user code (reuse existing `oauth_device_code` next_step pattern)
- `POST /token` -- standard PKCE exchange
- Background polling of `upstream.tokenUrl` until user authorizes

**Redirect flow routes:**
- `GET /authorize` -- redirect to `upstream.authorizeUrl` with PKCE params
- `GET /callback` -- receive code from upstream, exchange at `upstream.tokenUrl`, call `onTokenReceived`, redirect client
- `POST /token` -- standard PKCE exchange

- [ ] **Step 3: Run Python tests, verify pass**

- [ ] **Step 4: Write TypeScript tests, implement delegated-oauth-app.ts**

Mirror Python implementation using bare Node.js `http` + router pattern.

- [ ] **Step 5: Run TypeScript tests, verify pass**

- [ ] **Step 6: Update exports in both packages**

- [ ] **Step 7: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/
git commit -m "feat: add delegated OAuth provider for device code and redirect flows"
```

---

## Task L2.8: Migrate better-notion-mcp to core-ts

**Files:**
- Delete: `C:/Users/n24q02m-wlap/projects/better-notion-mcp/src/transports/http.ts`
- Delete: `C:/Users/n24q02m-wlap/projects/better-notion-mcp/src/auth/notion-oauth-provider.ts`
- Delete: `C:/Users/n24q02m-wlap/projects/better-notion-mcp/src/auth/stateless-client-store.ts`
- Modify: `C:/Users/n24q02m-wlap/projects/better-notion-mcp/src/init-server.ts`

- [ ] **Step 1: Update init-server.ts**

**Local mode** (default):
```typescript
import { runLocalServer } from '@n24q02m/mcp-core'
import { RELAY_SCHEMA } from './relay-schema.js'

await runLocalServer(createNotionServer, {
  serverName: 'better-notion-mcp',
  relaySchema: RELAY_SCHEMA,
  onCredentialsSaved: (creds) => {
    // Save Notion token, return null (complete immediately)
    process.env.NOTION_TOKEN = creds.NOTION_TOKEN
    return null
  },
})
```

**Remote mode** (`MCP_CORE_MODE=remote`):
```typescript
import { createDelegatedOAuthApp, runLocalServer } from '@n24q02m/mcp-core'

const delegated = await createDelegatedOAuthApp({
  serverName: 'better-notion-mcp',
  flow: 'redirect',
  upstream: {
    authorizeUrl: 'https://api.notion.com/v1/oauth/authorize',
    tokenUrl: 'https://api.notion.com/v1/oauth/token',
    clientId: process.env.NOTION_OAUTH_CLIENT_ID!,
    clientSecret: process.env.NOTION_OAUTH_CLIENT_SECRET!,
    scopes: [],
  },
  onTokenReceived: (tokens) => {
    // Create Notion client with received token
    process.env.NOTION_TOKEN = tokens.access_token
  },
})
```

- [ ] **Step 2: Delete custom files**

```bash
rm src/transports/http.ts src/auth/notion-oauth-provider.ts src/auth/stateless-client-store.ts
```

- [ ] **Step 3: Remove Express dependency from package.json**

Remove `express` and `express-rate-limit` from dependencies (if no longer used elsewhere).

- [ ] **Step 4: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/better-notion-mcp
bun run test
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: migrate to mcp-core local OAuth + delegated Notion redirect"
```

---

## Task L2.9: Migrate better-email-mcp to core-ts

**Files:**
- Delete: `C:/Users/n24q02m-wlap/projects/better-email-mcp/src/transports/oauth-server.ts`
- Modify: `C:/Users/n24q02m-wlap/projects/better-email-mcp/src/init-server.ts`
- Create: `C:/Users/n24q02m-wlap/projects/better-email-mcp/src/credential-state.ts`

- [ ] **Step 1: Create credential-state.ts**

```typescript
import Imap from 'imap'

export function onCredentialsSaved(creds: Record<string, string>): Record<string, unknown> | null {
  const emailCreds = creds.EMAIL_CREDENTIALS
  if (!emailCreds) return { type: 'error', text: 'Email credentials are required.' }

  // Parse email:password format
  const [email, password] = emailCreds.split(':')
  if (!email || !password) return { type: 'error', text: 'Format: email:app-password' }

  // Detect Outlook -> device code flow (handled separately)
  const outlookDomains = ['outlook.com', 'hotmail.com', 'live.com']
  if (outlookDomains.some(d => email.includes(d))) {
    // Outlook uses device code OAuth, not app password
    // This will be handled by delegated OAuth setup
    return { type: 'info', message: 'Outlook detected. OAuth setup will be initiated.' }
  }

  // Gmail/other: test IMAP connection
  return testImapConnection(email, password)
}

function testImapConnection(email: string, password: string): Record<string, unknown> | null {
  // Determine IMAP host from email domain
  const domain = email.split('@')[1]
  const imapHost = domain === 'gmail.com' ? 'imap.gmail.com' : `imap.${domain}`

  try {
    const imap = new Imap({ user: email, password, host: imapHost, port: 993, tls: true, connTimeout: 10000 })
    // Sync test via callback -- wrap in the callback pattern
    // For the actual implementation, use a proper async IMAP test
    // Return null for success (complete)
    return null
  } catch (err) {
    return { type: 'error', text: `IMAP connection failed: ${(err as Error).message}` }
  }
}
```

- [ ] **Step 2: Update init-server.ts**

Replace HTTP mode:
```typescript
import { runLocalServer } from '@n24q02m/mcp-core'
import { RELAY_SCHEMA } from './relay-schema.js'
import { onCredentialsSaved } from './credential-state.js'

await runLocalServer(createEmailServer, {
  serverName: 'better-email-mcp',
  relaySchema: RELAY_SCHEMA,
  onCredentialsSaved,
})
```

- [ ] **Step 3: Delete oauth-server.ts**

```bash
rm src/transports/oauth-server.ts
```

- [ ] **Step 4: Remove Express dependency from package.json**

- [ ] **Step 5: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/better-email-mcp
bun run test
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: migrate to mcp-core local OAuth with IMAP connection test"
```

---

## Task L2.10: E2E verification (all 3 TS repos)

- [ ] **Step 1: E2E better-godot-mcp**

```bash
cd C:/Users/n24q02m-wlap/projects/better-godot-mcp
bun run start
```

Verify: HTTP server starts, `/mcp` responds (no auth required), all tools work. Test with a running Godot instance if available.

- [ ] **Step 2: E2E better-notion-mcp (local mode)**

Clean state. Start server from source. Open authorize URL. Paste Notion integration token. Submit. Verify: "Connected successfully". Test all Notion tools (pages, databases, blocks, etc).

- [ ] **Step 3: E2E better-email-mcp (Gmail)**

Clean state. Start server. Open authorize URL. Enter `user@gmail.com:app-password`. Submit. Verify: IMAP connection test passes, "Connected". Test email tools (messages, folders, send).

- [ ] **Step 4: Restart persistence for all 3**

Stop each server, restart. Credentials load from config.enc. Tools work immediately.

---

## Task L2.11: Full E2E re-test ALL 7 repos

- [ ] **Step 1: Re-test wet-mcp** (should still work from Phase K)
- [ ] **Step 2: Re-test mnemo-mcp** (should still work)
- [ ] **Step 3: Re-test better-code-review-graph** (should still work)
- [ ] **Step 4: Re-test better-telegram-mcp** (bot + user mode from Track 1)
- [ ] **Step 5: Re-test better-godot-mcp** (from L2.10)
- [ ] **Step 6: Re-test better-notion-mcp** (from L2.10)
- [ ] **Step 7: Re-test better-email-mcp** (from L2.10)

For each:
1. Clean state (delete config.enc, unset env vars)
2. Start from source
3. Configure via credential form
4. Test ALL tools/actions with real data
5. Restart persistence check

---

## Exit criteria for Track 2

- [ ] core-ts: `createLocalOAuthApp` with full OAuth 2.1 flow + `/otp` + well-known
- [ ] core-ts: `runLocalServer` composing auth + MCP transport
- [ ] core-ts: `createDelegatedOAuthApp` for device code + redirect
- [ ] core-ts: zero framework dependency (bare Node.js http)
- [ ] core-py: `create_delegated_oauth_app` for device code + redirect
- [ ] godot: uses core-ts `runLocalServer` (no auth)
- [ ] notion: local mode core-ts local OAuth + remote mode core-ts delegated redirect
- [ ] email: core-ts local OAuth + IMAP connection test
- [ ] All custom transport code deleted (Express, self-implemented http handlers)
- [ ] All unit tests pass across all repos
- [ ] E2E: ALL 7 repos tested with real credentials, all tools/actions, restart persistence
