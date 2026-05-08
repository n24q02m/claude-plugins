---
title: Architecture
description: How mcp-core is built and what it provides to consumer servers.
---

`mcp-core` is the foundation library every server in this stack consumes. It is **not a server** — you don't install or run mcp-core. Other servers depend on it via npm (`@n24q02m/mcp-core`) or PyPI (`mcp-core`).

## What it provides

- **Streamable HTTP transport** — implements MCP 2025-11-25 transport spec for both client and server roles.
- **OAuth 2.1 Authorization Server primitives** — DCR (Dynamic Client Registration), `/authorize`, `/token`, `/.well-known/oauth-authorization-server`, JWT signing/verification.
- **Lifecycle** — server boot, daemon spawn, browser-open helpers, graceful shutdown.
- **Per-JWT-sub credential storage** — encrypted bundle keyed on `<server>:<sub>`, AES-256-GCM, pluggable backend (SQLite default, Postgres / Redis available).
- **Relay form** — shared HTML form rendered identically by `local-relay` and `remote-relay` modes.
- **State machines** — credential bootstrap, OAuth code exchange, daemon recovery.

## Two implementations

mcp-core ships in two languages because consumers vary:

- **`@n24q02m/mcp-core`** (TypeScript / Node) — used by `better-notion-mcp`, `better-email-mcp`, `better-godot-mcp`.
- **`mcp-core`** (Python) — used by `wet-mcp`, `mnemo-mcp`, `better-code-review-graph`, `imagine-mcp`, `better-telegram-mcp`.

Both implementations track the same MCP spec version and ship in lockstep.

## Repo layout

```
mcp-core/
├── packages/                    npm workspace
│   ├── core-ts/                 @n24q02m/mcp-core (TypeScript)
│   └── core-py/                 mcp-core (Python; uv project)
├── docs/                        deep-dive docs (you're reading the migrated copies)
└── shared-services/             docker-compose for ancillary services
```

## Trust model

See [trust model](/servers/mcp-core/trust-model/) for the formal threat model. Headlines:

- Server-side state is encrypted at rest with `KEYRING_SECRET`.
- JWT signing keys are server-controlled in `remote-oauth` mode; consumers must verify against the server's JWKS.
- Same-origin policy enforced on `/authorize` (CSRF protection via `state` param).
- No telemetry — server never phones home with user credentials or tool invocations.

## Migration history

See [migration](/servers/mcp-core/migration/) for breaking-change notes from previous core libraries.

## Shared services

See [shared services](/servers/mcp-core/shared-services/) for the docker-compose stack of ancillary services (search backend, etc.) some MCP servers spin up locally.

## Repo + releases

- Source: [github.com/n24q02m/mcp-core](https://github.com/n24q02m/mcp-core)
- Releases (TS): [npmjs.com/package/@n24q02m/mcp-core](https://www.npmjs.com/package/@n24q02m/mcp-core)
- Releases (Py): [pypi.org/project/mcp-core/](https://pypi.org/project/mcp-core/)
- License: MIT
