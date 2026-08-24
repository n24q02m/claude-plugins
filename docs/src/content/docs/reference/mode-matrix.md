---
title: Mode matrix
description: Which server supports which mode.
---

Each server has a fixed set of supported modes. Pick based on your scenario; switching modes is supported but requires re-bootstrap of credentials.

## Server × mode

| Server | stdio | local-relay | remote-relay | remote-oauth | Default |
|---|:-:|:-:|:-:|:-:|---|
| `mcp-core` | — | — | — | — | (foundation library, not a server) |
| `wet-mcp` | yes | yes | yes | — | `stdio` |
| `mnemo-mcp` | yes | yes | yes | — | `stdio` |
| `better-code-review-graph` | yes | yes | yes | — | `stdio` |
| `imagine-mcp` | yes | yes | yes | — | `stdio` |
| `better-telegram-mcp` | yes | yes | yes | yes | `stdio` |
| `better-notion-mcp` | yes | yes | yes | yes | `stdio` |
| `better-email-mcp` | yes | yes | yes | yes | `stdio` |
| `better-godot-mcp` | yes | — | — | — | `stdio` |
| `better-workspace-mcp` | yes | — | — | yes | `stdio` |

## Mode definitions

### stdio

Server runs as a child of the MCP client over stdin/stdout. Credentials in client config (`mcp.json` `env` block). No daemon, no persistent storage. Simplest mode; no shared state.

### local-relay

Client spawns a local HTTP daemon. Daemon opens a browser at first run for credential entry. Credentials encrypted and persisted at `~/.config/<server>/config.enc`. Subsequent client runs reuse the daemon if alive.

### remote-relay

Same form/flow as `local-relay` but the HTTP server is your self-hosted deployment (e.g. Docker on a VM). Credentials scoped per JWT subject. One deploy serves N users.

### remote-oauth

Self-hosted server doubles as an OAuth 2.1 Authorization Server. Standard OAuth flow for client identity. User identity (sub) supplied by an upstream IdP (GitHub / Google). Credential storage still per-sub.

## Default mode rationale

The default is what the marketplace `plugin.json` installs. Every current server
plugin defaults to local `stdio`; relay/OAuth modes are explicit self-hosted
overrides. Telegram's former managed hosted runtime is retired, while its
self-hosted `remote-relay` and `remote-oauth` modes remain supported.

`better-workspace-mcp` has no credential-paste relay mode: Google credentials
are never pasted, because the user consents on Google's own screen. In stdio
that consent returns to a loopback address; in `remote-oauth` it returns to
`/accounts/callback` on the deployment, so the two modes need different Google
OAuth client types (Desktop vs Web application).

## Anti-patterns

- Mixing modes for the same server install — pick one and stick with it. Switching modes invalidates persisted credentials.
- Sharing `config.enc` across machines — `local-relay` storage is single-user. Use `remote-relay` if you need team access.
- Self-hosting `remote-relay` without a JWT issuer — every request gets the same `sub` and credentials silently overlap.
