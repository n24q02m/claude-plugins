---
title: Mode matrix
description: Which server supports which mode.
---

Each server has a fixed set of supported modes. Pick based on your scenario; switching modes is supported but requires re-bootstrap of credentials.

## Server × mode

| Server | stdio | local-relay | remote-relay | remote-oauth | Default |
|---|:-:|:-:|:-:|:-:|---|
| `mcp-core` | — | — | — | — | (foundation library, not a server) |
| `wet-mcp` | yes | yes | yes | — | `local-relay` |
| `mnemo-mcp` | yes | yes | yes | — | `local-relay` |
| `better-code-review-graph` | yes | yes | yes | — | `local-relay` |
| `imagine-mcp` | yes | yes | yes | — | `local-relay` |
| `better-telegram-mcp` | yes | yes | yes | yes | `remote-relay` |
| `better-notion-mcp` | yes | yes | yes | yes | `remote-oauth` |
| `better-email-mcp` | yes | yes | yes | yes | `remote-relay` |
| `better-godot-mcp` | yes | — | — | — | `stdio` |

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

The default is what the plugin manifest sets in `mcp.json` when installed via marketplace. Override per-install if needed. Most servers default to `local-relay` (single-user with browser flow). `better-godot-mcp` defaults to `stdio` (no credentials needed). Notion/Email/Telegram default to remote because team-shared deploy is the common deployment pattern.

## Anti-patterns

- Mixing modes for the same server install — pick one and stick with it. Switching modes invalidates persisted credentials.
- Sharing `config.enc` across machines — `local-relay` storage is single-user. Use `remote-relay` if you need team access.
- Self-hosting `remote-relay` without a JWT issuer — every request gets the same `sub` and credentials silently overlap.
