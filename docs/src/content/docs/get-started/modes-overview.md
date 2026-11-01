---
title: Modes overview
description: stdio or self-hosted HTTP, plus the three HTTP auth modes — pick the right setup for your scenario.
---

Every MCP server in this stack runs on a machine you control. There is no n24q02m-hosted endpoint and no browser form for entering credentials: credentials come from environment variables, the server's local CLI (`<server> auth`), or its `config` tool.

A server is started in one of two **transports**. Over HTTP it additionally runs in one of three **auth modes**.

## The transports

| Transport | Where the server runs | When to use |
|---|---|---|
| `stdio` | Child process of the MCP client, over stdin/stdout | Simplest. One user on one machine. |
| `http` | A process you start (locally or on a host you operate), serving MCP at `/mcp` | A long-running local server, or one install shared by several people. |

`http` binds to loopback (`127.0.0.1`) by default. To reach it from other machines, put your own TLS reverse proxy in front of it.

## HTTP auth modes

| Auth mode | Who can call the server | Notes |
|---|---|---|
| `no-auth` | Anyone who can reach the port | Loopback bind only. The server refuses to start on a non-loopback host. |
| `token` | Holders of one shared bearer token | The server stores only the token's hash; mint it with `<server> token hash`. |
| `multi` | Each user holds their own bearer token | A users file maps every token to a credential namespace, so users never see each other's credentials. See [Multi-user setup](/get-started/multi-user/). |

## Decision flow

Pick `stdio` if you use one client on one machine. It is the default for telegram, notion, email, workspace and crg.

Pick `http` with `no-auth` if you want a long-running local server and nothing else can reach your loopback port. Wet and Mnemo only offer HTTP, so this is their simplest setup.

Pick `http` with `token` if you expose the server beyond loopback for yourself or a small trusted group that shares one identity.

Pick `http` with `multi` if several people use the same install and must not share credentials.

## What every server supports

Not every server offers every transport or auth mode. The [mode matrix](/reference/mode-matrix/) lists them per server, and each server's setup page gives the exact config keys and environment variables.

## Where credentials come from

See [Credential setup](/reference/credential-setup/) for the full picture. In short:

- `stdio`: environment variables in your client config (for example `NOTION_TOKEN`), or credentials saved earlier with `<server> auth`.
- `http`: credentials the operator saves on the host with `<server> auth --user <namespace>`, or that each user sets through the `config` tool, depending on the server.

## Coming from older docs

Earlier versions of these docs described `local-relay`, `remote-relay` and `remote-oauth` modes with a browser credential form. Those modes were removed. Use `stdio` or `http` as above, and enter credentials again with environment variables or `<server> auth` (telegram migrates its previously saved configuration automatically).

## Read on

- [Multi-user setup](/get-started/multi-user/) — per-namespace credential model
- [Mode matrix](/reference/mode-matrix/) — which server supports which transport and auth mode
- [Credential setup](/reference/credential-setup/) — how credentials reach a server
