---
title: Multi-user pattern
description: Users file + per-namespace credential storage recipe for HTTP multi auth.
---

Multi-user is the HTTP `multi` auth mode. One self-hosted server serves several users; each user's credentials are stored in their own **namespace**, selected by the bearer token they send. Servers that support `multi` are listed in the [mode matrix](/reference/mode-matrix/).

## Required components

1. **A bearer token per user.** You mint them; the server does not issue tokens and runs no OAuth authorization server. Hash each token with the server's `token hash` command (the token is read from stdin or a prompt, never argv) and keep only the hash.

2. **A users file.** One entry per user: token hash, `enabled` flag, and the namespace they map to.

   ```toml
   [users.alice]
   token_hash = "scrypt$..."
   enabled = true
   namespace = "alice"
   ```

   The file location comes from the server's config (`[server] users_file`) or its `*_USERS_FILE` environment variable. You edit it on the host and restart the server.

3. **A reverse proxy for TLS** when clients are not on the same machine. The server binds to loopback by default and does not terminate TLS.

## Storage layout

Credentials are encrypted at rest and kept per namespace under the server's data directory (`~/.<server>/`):

```
~/.telegram/config.json                  # default namespace (stdio, no-auth, token)
~/.telegram/subs/alice/config.json       # namespace "alice" (multi)
~/.telegram/subs/bob/config.json         # namespace "bob"   (multi)
```

Different namespaces never read each other's files, and different servers keep separate data directories.

## What's in a stored entry

An encrypted blob with the credential payload (AES-256-GCM). The key is a machine key in `~/.<server>/.secret` (owner-only permissions); for `workspace` over HTTP it is derived from the `CREDENTIAL_SECRET` environment variable, and the server refuses to start without it. Session files, where a server has them (Telegram), sit beside the entry with `600` permissions.

## Operating a multi deployment

- **Add a user**: mint a token, hash it, add an entry, restart. Set the user's credentials with the server's CLI (`<server> auth --user <namespace>`) or let the user call the `config` tool, as the server's setup page describes.
- **Disable a user**: set `enabled = false` and restart. Their stored credentials remain until you delete the namespace or run `<server> logout --user <namespace>` where available.
- **Offboard a user**: disable them, revoke the upstream credential (for example the bot token), then delete their namespace directory.

## Anti-patterns

- Reusing one token for several users: every request lands in the same namespace and credentials overlap.
- Passing tokens in the URL query string (`?token=xxx`): they leak via referer headers and access logs.
- Exposing the port without TLS and without a token hash: use a reverse proxy, and never bind `no-auth` beyond loopback.
- Leaving a departed user's token in the users file and relying on the upstream account being closed.

## Read more

- [Modes overview](/get-started/modes-overview/)
- [Credential setup](/reference/credential-setup/)
