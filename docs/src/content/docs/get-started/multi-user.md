---
title: Multi-user setup
description: Self-host one server, share it with a team — each user has their own credentials.
---

In HTTP `multi` auth mode, one deployed server serves several users without mixing their credentials. Each user holds their own **bearer token**; the server maps that token to a **namespace**, and every namespace has its own encrypted credential storage.

## How it works

1. You (the operator) mint a bearer token for each user and keep only its hash. Most servers provide `<server> token hash`, which reads the token from stdin or a prompt so it never lands in shell history.
2. You list the users in the server's users file, one entry per user with the token hash, an `enabled` flag and the namespace they map to:

   ```toml
   # ~/.telegram/users.toml (path is set by `[server] users_file`)
   [users.alice]
   token_hash = "scrypt$..."
   enabled = true
   namespace = "alice"
   ```

3. The user's client sends `Authorization: Bearer <token>` on every request. A request without a valid token for an enabled user is rejected.
4. The server resolves the token to its namespace and reads and writes credentials only in that namespace. Credentials for the `default` namespace live in the server's data directory; other namespaces live under `subs/<namespace>/` beside it.

Users are administered on the host: edit the users file and restart the server. An invalid users file makes the server print one line to stderr and exit with code 2.

## Setting a user's credentials

The credentials for a namespace are set in one of two ways, depending on the server:

- The operator runs the server's CLI on the host: `telegram auth --user <namespace>` (bot token, or phone + OTP + 2FA) or `workspace auth --user <namespace>` (Google consent).
- The user calls the server's `config` tool over their authenticated session (notion).

The server's setup page says which one applies.

## Deployment

Start the server with `--http` (or `MCP_TRANSPORT=http`) and configure `[server]` in its config file, for example:

```toml
# ~/.telegram/config.toml
[server]
host = "127.0.0.1"   # default; keep loopback and put a reverse proxy in front
port = 8000
auth = "multi"
users_file = "users.toml"
```

Servers that publish a `docker-compose.http.yml` (notion, email, workspace) bind the container to loopback on the host. Put your own TLS-terminating reverse proxy (Caddy, nginx, a Cloudflare Tunnel) in front of it; the server itself never terminates TLS for you.

## What about stdio?

`stdio` is single-user by design. No namespace is involved and credentials come from the environment or the default namespace. Do not copy a server's data directory between machines: it is encrypted with a machine key that stays on the original host.

## Read on

- [Modes overview](/get-started/modes-overview/) — pick the right transport and auth mode
- [Multi-user pattern](/reference/multi-user-pattern/) — storage layout and operating rules
