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

## Browser doesn't auto-open during relay flow

Symptom: server starts but no browser appears for credential entry.

Workaround: open the URL printed in the server's stderr log manually. Look for a line like:

```
[relay] Open this URL in your browser to configure credentials:
[relay]   http://localhost:38765/authorize
```

If your client redirects all stderr to a file, check there.

## "Authorization required" loop on remote-relay

Symptom: every tool call returns 401 with "Re-authorize required" even after submitting credentials.

Check JWT `sub` claim: server stores per-subject. If your client is sending different `sub` values across calls (e.g. session expired and re-auth produced new sub), credentials get scoped to the new sub. Your old credentials still exist but for the old sub.

Fix: either (a) authenticate once and stay logged in, or (b) re-submit credentials under the new sub.

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
- Mode (stdio / local-relay / remote-relay / remote-oauth)
- Last 50 lines of server stderr
- Minimal reproduction steps

Server-specific issue templates link from each `/servers/<name>/troubleshooting/` page.
