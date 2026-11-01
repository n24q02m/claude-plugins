---
title: Mode matrix
description: Which server supports which transport and HTTP auth mode.
---

Every server runs on a machine you control. A server offers `stdio`, `http`, or both; over `http` it supports one or more auth modes (`no-auth`, `token`, `multi`). See the [modes overview](/get-started/modes-overview/) for what each means. There is no hosted endpoint and no browser credential form.

## Server x mode

| Server | stdio | http | HTTP auth modes | Default |
|---|:-:|:-:|---|---|
| `hull` | — | — | — | (foundation library, not a server) |
| `wet` | — | yes | `no-auth`, `token`, `multi` | `http` (only transport) |
| `mnemo` | — | yes | `no-auth`, `token`, `multi` | `http` (only transport) |
| `crg` | yes | — | — | `stdio` |
| `telegram` | yes | yes | `no-auth`, `token`, `multi` | `stdio` |
| `notion` | yes | yes | `multi` (default), `token`, `no-auth` | `stdio` |
| `email` | yes | yes | `token` (single user), `no-auth` (loopback only) | `stdio` |
| `workspace` | yes | yes | `multi` | `stdio` |
| `imagine-mcp` †, `better-godot-mcp` † | — | — | — | archived; not covered by this matrix |

(† archived — docs kept for reference, project no longer maintained.)

## Definitions

### stdio

The server runs as a child of the MCP client over stdin/stdout. Credentials come from the client config (`mcp.json` `env` block) or from credentials saved earlier with the server's CLI. No separate process to manage.

### http

You start the server (`--http`, or `MCP_TRANSPORT=http`; Wet and Mnemo are always HTTP) and the client connects to `http://<host>:<port>/mcp`. It binds to loopback by default.

### HTTP auth modes

- `no-auth`: no token. Loopback bind only; a non-loopback host is refused at startup.
- `token`: one shared bearer token. The server keeps only its hash.
- `multi`: one bearer token per user, mapped to a credential namespace by a users file. See [Multi-user setup](/get-started/multi-user/).

## Default transport rationale

`stdio` is the default wherever the server can run as a child process: no setup beyond credentials. Wet and Mnemo are HTTP-only because they hold a long-lived local index and models, so one process serves every client on the machine.

`workspace` never takes pasted Google credentials: the user consents on Google's own screen. In `stdio` that consent returns to a loopback address; in `http` the operator runs `workspace auth --user <namespace>` on the host to consent for each namespace. The two paths use different Google OAuth client types (Desktop for `stdio`, Web application for `http`).

## Anti-patterns

- Binding `no-auth` beyond loopback. The server refuses to start; use `token` or `multi` and a TLS reverse proxy instead.
- Copying a server's data directory between machines. Saved credentials are encrypted with a machine key that stays on the original host.
- Using `multi` with a single shared token. Give each person their own token and namespace, otherwise credentials overlap.
- Passing credentials or tokens in a URL query string (`?token=xxx`). They leak through referer headers and access logs.
