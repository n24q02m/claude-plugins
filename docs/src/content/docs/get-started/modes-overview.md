---
title: Modes overview
description: stdio / local-relay / remote-relay / remote-oauth — pick the right mode for your scenario.
---

Every MCP server in this stack supports a fixed set of "modes" that determine how credentials are bootstrapped and where the server runs. Pick one based on your scenario.

## The four modes

| Mode | Where server runs | Where credentials live | When to use |
|---|---|---|---|
| `stdio` | Same process as the client | Client config (`mcp.json` `env`) | Simplest. Solo dev, no shared state. |
| `local-relay` | Local daemon spawned by client | Encrypted file at `~/.config/<server>/config.enc` | Browser-based credential entry. Single user. |
| `remote-relay` | Self-hosted HTTP server | Per-JWT-sub on the remote server | Team. Shared deploy. Each user has own creds. |
| `remote-oauth` | Self-hosted HTTP server with OAuth AS | Per-JWT-sub via OAuth provider | Team + audit. OIDC SSO for credential storage. |

## Decision flow

Pick `stdio` if you have all credentials as env vars and run solo.

Pick `local-relay` if your credentials require a browser flow (OAuth, paste-token form) and you're solo. The server opens a browser at first run, you fill the form, the server encrypts and persists `config.enc` locally.

Pick `remote-relay` if multiple people use the same server install and you don't want to share credentials. Each user authenticates against your deployed instance and has own credentials scoped to their JWT subject.

Pick `remote-oauth` if you want OIDC SSO (GitHub, Google) on top of `remote-relay`. Credentials still per-JWT-sub but identity comes from a real provider.

## What every server supports

Not every server supports every mode. Each server's `/servers/<name>/modes/` page lists supported modes plus the relay/OAuth-specific config schema.

## Same UI across modes

Per `relay-mode-ui-parity` rule (mcp-dev), `local-relay` and `remote-relay` show the **identical** form to the user. Only the storage scope differs (single-user `config.enc` vs per-JWT-sub on server).

## Read on

- [Multi-user setup](/get-started/multi-user/) — per-JWT-sub credential model
- [Mode matrix](/reference/mode-matrix/) — which server supports which mode
- [Relay flow](/reference/relay-flow/) — credential bootstrap state machine
