---
title: Troubleshooting
description: Daemon, stale lock, browser, and other common issues.
---

## Daemon won't start

Symptom: client (Claude Code, Codex) fails to connect to MCP server. Logs show "Failed to spawn daemon" or "Connection refused".

Check:

```sh
ps aux | grep <server-name>      # macOS / Linux
Get-Process <server-name>        # PowerShell
```

If a stale process is running, kill it:

```sh
pkill -f <server-name>
```

## Stale lock file

Symptom: server fails with "Another instance is running" but no process exists.

Find the lock:

```sh
ls ~/.config/<server-name>/*.lock
```

Delete it:

```sh
rm ~/.config/<server-name>/*.lock
```

Restart your client.

## Server exits immediately with a credentials hint

Symptom: in `stdio` mode the server prints a hint to stderr and exits before any MCP output (for example the `telegram auth` hint, or a message that `NOTION_TOKEN` is unset).

Fix: set the environment variable the message names in your client config, or save credentials once with the server's CLI (`<server> auth`) and restart the client. Your client may hide stderr; run the server command in a terminal to read the message.

## Server exits with code 2 at startup

Symptom: the HTTP server prints a single line to stderr and exits with code 2.

Common causes:
- `auth = "no-auth"` with a non-loopback `host`. `no-auth` is loopback-only; use `token` or `multi` to bind elsewhere.
- An invalid `config.toml` or users file. The line names the file and the problem.

## 401 Unauthorized on HTTP

Symptom: every request to the HTTP server returns 401.

Check:
- The client sends `Authorization: Bearer <token>`, and the token matches the `token_hash` in the server config (`token` mode) or an enabled entry in the users file (`multi` mode).
- You restarted the server after editing the users file.
- In `multi` mode, the token belongs to the user you expect: credentials are stored per namespace, so a different token reaches different (possibly empty) credentials.

## Rate limits

Some servers proxy upstream APIs (Notion, Telegram, Gemini). Upstream rate limits propagate as 429 errors. Server logs the upstream response.

Strategy:
- Notion: 3 req/s/integration — tools are designed to batch
- Telegram Bot API: 30 req/s — far above typical agent usage
- Gemini: tier-dependent

## Filing a bug

If none of the above help, open an issue on the server's GitHub repo with:
- OS + version
- Server version (`<server-name> --version`)
- Transport and auth mode (`stdio`, or `http` with `no-auth` / `token` / `multi`)
- Last 50 lines of server stderr
- Minimal reproduction steps

Server-specific issue templates link from each `/servers/<name>/troubleshooting/` page.
