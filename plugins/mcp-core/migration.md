---
title: Migration
description: Migration history of mcp-core.
---

## Migration to v1 (2026-04-30)

# Migration Guide: mcp-core 1.12.0 — Multi-Mode (stdio + HTTP) Architecture

**Audience:** users of `n24q02m-mcp-core` / `@n24q02m/mcp-core` and any of the
8 downstream MCP plugins (wet, mnemo, better-code-review-graph, imagine,
better-telegram, better-notion, better-email, better-godot).

**Effective:** mcp-core 1.12.0 onward. Smart_stdio bridge for stdio path is
soft-deprecated in this release and scheduled for hard removal in 2.0.0.


## User action required

After upgrading mcp-core to 1.12.0, run the cleanup CLI **once** to
terminate any leftover bridge daemons and remove their lock + cache
state:

```bash
mcp-clean-state --kill-daemons
```

This:

1. Iterates every `*.lock` file under `~/.config/mcp/locks/`
   (or `%LOCALAPPDATA%\mcp\locks\` on Windows).
2. Parses the daemon PID from line 0 of each lock.
3. If the PID is alive, terminates the process (cross-platform: SIGKILL
   on POSIX, `TerminateProcess` on Windows).
4. Removes the `*.lock` file plus matching `*.tools.json` companion in
   the cache directory and any `*.tools-list-changed` sentinel.

Output:

```
Killed N daemons; cleaned M lock files.
```

If you skip this step, leftover bridge daemons continue to listen on their
random ports (harmless but wasteful) until the next reboot or 24h TTL sweep.
The next stdio plugin invocation does **not** consult these old daemons —
it spawns a new direct FastMCP stdio process instead — so there is no
correctness risk, only resource leak.


## Plugin developer guidance

If you import `mcp_core` (Python) or `@n24q02m/mcp-core` (TypeScript) inside
your own plugin code, the API surface changes are:

### Python — API kept

| Symbol | Status | Notes |
|---|---|---|
| `mcp_core.transport.run_http_daemon` | NEW (1.12.0) | Renamed from `run_local_server`; alias preserved. |
| `mcp_core.transport.run_local_server` | KEPT (alias) | Calls `run_http_daemon`. Still works in 1.x. |
| `mcp_core.config.*` | KEPT | Config storage primitives (`load_config`, `save_config`, `config.enc`). |
| `mcp_core.crypto.*` | KEPT | ECDH P-256 + AES-256-GCM helpers. |
| `mcp_core.relay.register_relay_form_tool` | NEW (1.12.0) | Transient HTTP relay form for stdio-mode credential setup. |
| `mcp_core.lifecycle.*` | KEPT | Lock file primitives still used by HTTP daemon mode. |
| `mcp_core.install.*` | KEPT | Plugin installer helpers. |

### Python — API deprecated (removed in 2.0.0)

| Symbol | Replacement |
|---|---|
| `mcp_core.transport.run_smart_stdio_proxy` | `mcp.run(transport="stdio")` directly inside the plugin's `main()`. Emits `DeprecationWarning` from 1.12.0. |
| `mcp_core.transport.persist_capabilities_cache` | No replacement — the `<lock>.tools.json` cache is no longer written for stdio path. HTTP daemon mode never used it. |
| Sentinel polling helpers (`watch_tools_list_changed`) | No replacement — sentinel auto-respawn was a stdio-bridge implementation detail. |

### TypeScript — API kept

| Symbol | Status | Notes |
|---|---|---|
| `runHttpDaemon` | NEW (1.12.0) | Renamed from `runLocalServer`; alias preserved. |
| `runLocalServer` | KEPT (alias) | Calls `runHttpDaemon`. |
| `loadConfig` / `saveConfig` | KEPT | Config storage. |
| `EcdhAesCrypto` | KEPT | Crypto parity with Python. |

### TypeScript — API deprecated (removed in 2.0.0)

| Symbol | Replacement |
|---|---|
| `runSmartStdioProxy` | `new StdioServerTransport()` from `@modelcontextprotocol/sdk/server/stdio.js`, then `await server.connect(transport)`. Emits deprecation warning. |

### Migration template — Python `main()`

Before (mcp-core ≤1.11):

```python
import os
import sys

from mcp_core.transport import run_smart_stdio_proxy

def main() -> None:
    if "--stdio" in sys.argv or os.environ.get("MCP_TRANSPORT") == "stdio":
        daemon_cmd = [sys.executable, "-m", "wet_mcp"]
        sys.exit(run_smart_stdio_proxy("wet-mcp", daemon_cmd))
    # ... HTTP path unchanged
```

After (mcp-core ≥1.12):

```python
import os
import sys

from wet_mcp.server import mcp  # Your FastMCP instance

def main() -> None:
    if "--stdio" in sys.argv or os.environ.get("MCP_TRANSPORT") == "stdio":
        # Direct FastMCP stdio — no bridge, no daemon, no lock file.
        # Universal MCP client compatibility.
        mcp.run(transport="stdio")
        return
    # ... HTTP path unchanged
```

### Migration template — TypeScript `main.ts`

Before:

```ts
import { runSmartStdioProxy } from '@n24q02m/mcp-core'

if (process.env.MCP_TRANSPORT === 'stdio') {
  const exit = await runSmartStdioProxy('better-notion-mcp', [process.argv[0], ...process.argv.slice(1)])
  process.exit(exit)
}
```

After:

```ts
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'

if (process.env.MCP_TRANSPORT === 'stdio') {
  const transport = new StdioServerTransport()
  await server.connect(transport)
  return
}
```

### Relay form for stdio-mode credential setup

If your plugin requires user credentials (e.g. an API key or OAuth flow)
and you are migrating to stdio mode, register the transient relay form
helper so users can configure credentials via a local browser tab:

```python
from mcp_core.relay import register_relay_form_tool
from wet_mcp.config import save_credentials  # Your callback

register_relay_form_tool(
    mcp,
    server_name="wet-mcp",
    on_save=save_credentials,  # Called with (server_name, creds_dict)
)
```

The helper registers a tool named `config__open_relay`. When the user
invokes that tool, the plugin spawns an in-process HTTP server on a
random local port, opens the user's browser to a credential form,
and self-shutdowns after submission or 10 minutes idle.


## Troubleshooting

### "ToolSearch finds nothing" after upgrade

Confirm:

1. `mcp-clean-state --kill-daemons` was run (kills leftover bridge daemons).
2. Restart your MCP client (Claude Code, Cursor, etc.) so it re-spawns the
   plugin process and re-discovers tools.
3. The plugin's manifest does **not** point at an old `n24q02m/<plugin>:latest`
   Docker image — pull `:stdio` or `:http` explicitly.

### "DeprecationWarning: run_smart_stdio_proxy"

Expected if you have a third-party plugin still using the old bridge import.
The plugin still works in 1.x; track its upgrade and pin to a 1.x mcp-core
release if you cannot wait.

### Bridge daemon won't terminate

`mcp-clean-state --kill-daemons` uses SIGKILL / `TerminateProcess`. If a
process survives, it likely was not the lock owner — manually kill via
your task manager and re-run the cleanup.


## Migration from mcp-relay-core

# Migration from mcp-relay-core to mcp-core

`mcp-core` is a functional **superset** of the now-archived
[`mcp-relay-core`](https://github.com/n24q02m/mcp-relay-core). The Python and
TypeScript public layouts are 1:1, so migrating a downstream server is a pure
import + dependency rename. Every symbol that lived in `mcp_relay_core.*` (or
`@n24q02m/mcp-relay-core/*`) lives at the same path under `mcp_core.*` (or
`@n24q02m/mcp-core/*`).

## Why migrate

- `mcp-relay-core` is **archived** as of 2026-04-11. No new releases.
- `mcp-core` adds the unified Streamable HTTP 2025-11-25 transport, OAuth 2.1
  Bearer middleware, lifecycle locks, install/agents config writer, and the
  shared embedding-daemon + stdio-proxy packages.
- All existing crypto / storage / OAuth / relay / schema modules are preserved
  byte-for-byte (with the package name substitution), so behavior is identical.

## Python (`packages/core-py`)

### Import rewrites

| Old (mcp-relay-core)                 | New (mcp-core)               |
|--------------------------------------|------------------------------|
| `from mcp_relay_core import X`       | `from mcp_core import X`     |
| `from mcp_relay_core.crypto.aes`     | `from mcp_core.crypto.aes`   |
| `from mcp_relay_core.crypto.ecdh`    | `from mcp_core.crypto.ecdh`  |
| `from mcp_relay_core.crypto.kdf`     | `from mcp_core.crypto.kdf`   |
| `from mcp_relay_core.storage.config_file`   | `from mcp_core.storage.config_file`  |
| `from mcp_relay_core.storage.encryption`    | `from mcp_core.storage.encryption`   |
| `from mcp_relay_core.storage.machine_id`    | `from mcp_core.storage.machine_id`   |
| `from mcp_relay_core.storage.mode`          | `from mcp_core.storage.mode`         |
| `from mcp_relay_core.storage.resolver`      | `from mcp_core.storage.resolver`     |
| `from mcp_relay_core.storage.session_lock`  | `from mcp_core.storage.session_lock` |
| `from mcp_relay_core.oauth import ...`      | `from mcp_core.oauth import ...`     |
| `from mcp_relay_core.relay.client`          | `from mcp_core.relay.client`         |
| `from mcp_relay_core.relay.browser`         | `from mcp_core.relay.browser`        |
| `from mcp_relay_core.relay.wordlist`        | `from mcp_core.relay.wordlist`       |
| `from mcp_relay_core.schema.types`          | `from mcp_core.schema.types`         |

In most server codebases this is a single sed command:

```bash
grep -rl "mcp_relay_core" src tests | xargs sed -i 's/mcp_relay_core/mcp_core/g'
```

### Dependency rename

`pyproject.toml`:

```diff
 [project]
 dependencies = [
-    "mcp-relay-core>=1.4.0",
+    "n24q02m-mcp-core>=1.0.0",
 ]
```

Note the PyPI package name is `n24q02m-mcp-core` (not `mcp-core`), but the
import path stays `mcp_core`.

After the rename, run `uv lock --upgrade-package n24q02m-mcp-core` (or your
project's lockfile equivalent) and commit.

### API changes you might notice

The Python port is byte-faithful with **two intentional bug fixes** that
surfaced under mcp-core's stricter `ty` type-check:

1. `mcp_core.relay.client.create_session(...)` now accepts an optional
   keyword-only `oauth_state: dict[str, str] | None = None` parameter. When
   non-None it is forwarded to the relay-server as `oauthState` in the POST
   body. Existing callers that did not pass `oauth_state` are unaffected.
2. `mcp_core.relay.client.RelaySession.public_key` is now
   `EllipticCurvePublicKey | None` instead of `EllipticCurvePublicKey`. This
   restores the documented "decrypt-only reconstructed session" use case in
   `OAuthProvider.exchange_code()`. No callers in mcp-relay-core read this
   field, so existing code is unaffected.

These two fixes lived as latent bugs in `mcp-relay-core/oauth/provider.py` —
that file referenced API signatures that did not exist in
`mcp-relay-core/relay/client.py`. The OAuth Provider was apparently never
exercised end-to-end on the Python side.

## TypeScript (`packages/core-ts`)

### Import rewrites

| Old (`@n24q02m/mcp-relay-core`) | New (`@n24q02m/mcp-core`) |
|---------------------------------|---------------------------|
| `from '@n24q02m/mcp-relay-core'`         | `from '@n24q02m/mcp-core'`         |
| `from '@n24q02m/mcp-relay-core/crypto'`  | `from '@n24q02m/mcp-core/crypto'`  |
| `from '@n24q02m/mcp-relay-core/storage'` | `from '@n24q02m/mcp-core/storage'` |
| `from '@n24q02m/mcp-relay-core/relay'`   | `from '@n24q02m/mcp-core/relay'`   |
| `from '@n24q02m/mcp-relay-core/schema'`  | `from '@n24q02m/mcp-core/schema'`  |
| `from '@n24q02m/mcp-relay-core/oauth'`   | `from '@n24q02m/mcp-core/oauth'`   |

Single sed command:

```bash
grep -rl "@n24q02m/mcp-relay-core" src tests | xargs sed -i 's|@n24q02m/mcp-relay-core|@n24q02m/mcp-core|g'
```

### Dependency rename

`package.json`:

```diff
 "dependencies": {
-  "@n24q02m/mcp-relay-core": "^1.1.0"
+  "@n24q02m/mcp-core": "^1.0.0"
 }
```

Run `bun install` (or `pnpm install` / `npm install`) and commit the lockfile.

## New features available (opt-in)

Once migrated, you can adopt these without further breaking changes:

- `mcp_core.transport.streamable_http.StreamableHTTPServer` and
  `@n24q02m/mcp-core/transport`'s `StreamableHTTPServer` — thin wrappers
  around the FastMCP / `@modelcontextprotocol/sdk` transports that integrate
  the lifecycle lock and OAuth middleware out of the box.
- `mcp_core.transport.oauth_middleware.OAuthMiddleware` (Python) /
  `OAuthMiddleware` (TypeScript) — RFC 6750 + RFC 9728 compliant Bearer token
  validation that returns 401 with
  `WWW-Authenticate: Bearer resource_metadata="..."`.
- `mcp_core.lifecycle.lock.LifecycleLock` — cross-platform file lock that
  prevents two server instances from binding the same `(name, port)` pair.
  Stores PID + port as readable metadata while the lock is held.
- `mcp_core.install.agents.AgentInstaller` — write or remove an MCP server
  entry in agent config files (Claude Code, Cursor, Codex, Windsurf, OpenCode).
- `mcp-embedding-daemon` PyPI package — shared FastAPI server scaffold for
  the upcoming ONNX/GGUF embedding backend. Exposes `/health` and
  scaffolded `/embed` + `/rerank` (501 with roadmap link).
- `mcp-stdio-proxy` PyPI package — `mcp-stdio-proxy` CLI that forwards
  stdio MCP frames to an HTTP MCP server, for agents without native HTTP.

## Verification checklist

After applying the rename in your downstream repo:

- [ ] `grep -rn "mcp_relay_core\|mcp-relay-core\|@n24q02m/mcp-relay-core" src tests` returns nothing
- [ ] `pyproject.toml` no longer references `mcp-relay-core`
- [ ] `package.json` no longer references `@n24q02m/mcp-relay-core`
- [ ] Lockfile regenerated and committed
- [ ] Test suite passes
- [ ] Lint + type check pass

If anything breaks, please open an issue at
<https://github.com/n24q02m/mcp-core/issues> with the error message and the
rename diff.
