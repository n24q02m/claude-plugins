# MCP Plugin Trust Model

This document defines the trust class for each MCP plugin x mode combination shipping in v1 of the n24q02m MCP stack.

## Why this matters

When you install an MCP plugin and grant it credentials (API keys, OAuth tokens, session cookies), those credentials live somewhere -- on disk, in memory, in a database, or in a hosted service. Different storage choices imply different trust assumptions about who can read your data.

This doc tells you, per plugin and per mode, exactly where credentials live and what threat model applies. If the doc says "TC-AdminTrust", you're trusting the operator (n24q02m for hosted instances, you-as-self-host operator otherwise). If it says "TC-NearZK", server compromise after restart yields no credentials.

## Trust Classes

### TC-Local -- machine-bound, single trust principal

- **Mode**: stdio + env, stdio + open_relay, HTTP self-host (single-user)
- **Storage**: `~/.<plugin>-mcp/config.json`, AES-GCM encrypted, machine-bound key from `~/.<plugin>-mcp/.secret` (auto-generated 32 bytes)
- **Trust principal**: OS user owns the process AND the key file (file perm 0600)
- **Threat model**:
  - Same-machine other OS users: blocked by file perm 0600
  - Lost laptop without disk encryption: adversary can read both `.secret` key file and `config.json` ciphertext = full compromise. Mitigate via FS encryption (BitLocker/LUKS/FileVault).
  - Memory dump while plugin running: key+plaintext recoverable (unavoidable for any local-decrypt model)

### TC-AdminTrust -- server-side encryption, admin holds key

- **Mode**: HTTP multi-user (legacy SaaS deploys before Phase 1; deprecated as of v1.0.0)
- **Storage**: `~/.<plugin>-mcp/subs/<sub>/config.json`, AES-GCM, key from PBKDF2(env `CREDENTIAL_SECRET`, salt=`<plugin>:<sub>`) (Python) or scrypt (TS)
- **Trust principal**: Server admin holds `CREDENTIAL_SECRET` env value and can decrypt all users' credentials
- **Threat model**:
  - NOT zero-knowledge: admin compromise = all users compromised
  - Acceptable for: trusted-operator SaaS where users have explicit relationship with the operator
  - Per-user salt prevents cross-user decryption with a single key derivation
- **Status in v1.0**: deprecated. Migrating to TC-NearZK in Phase 1 Task 7 of trust-model-alignment spec.

### TC-NearZK -- in-memory, ephemeral

- **Mode**: HTTP multi-user (SaaS hosted v1.0+)
- **Storage**: in-memory `Map<sub, creds>` (TS) or `dict[sub] = creds` (Python). NO disk persistence.
- **Trust principal**: server has access during request lifetime; restart clears all credentials
- **Threat model**:
  - Closer to zero-knowledge than TC-AdminTrust: admin debugger access can dump live memory but no persistent compromise
  - Filesystem dump after server restart: empty (no credential file to read)
  - Tradeoff: users re-OAuth after server restart (acceptable for OAuth flows where refresh-token UX is established)

## Per-Plugin Classification (v1.0.0)

| Plugin | Default mode | Trust class | Storage location |
|---|---|---|---|
| `wet-mcp` | stdio | TC-Local | `~/.wet-mcp/config.json` |
| `mnemo-mcp` | stdio | TC-Local | `~/.mnemo-mcp/config.json` |
| `better-code-review-graph` | stdio | TC-Local | `~/.better-code-review-graph-mcp/config.json` |
| `imagine-mcp` | stdio | TC-Local | `~/.imagine-mcp/config.json` |
| `better-godot-mcp` | stdio | TC-Local (no auth required) | N/A (no credentials) |
| `better-notion-mcp` | stdio | TC-Local | `~/.better-notion-mcp/config.json` |
| `better-email-mcp` | stdio | TC-Local | `~/.better-email-mcp/config.json` |
| `better-telegram-mcp` | stdio | TC-Local | `~/.better-telegram-mcp/config.json` |

## Self-host vs hosted

For each plugin, you can choose:

- **Stdio direct** (default for ALL credentialed plugins): the plugin runs as a subprocess of your MCP client (Claude Code, Cursor, Copilot, etc.). Credentials stored at `~/.<plugin>-mcp/config.json` per TC-Local. No network egress, no shared servers, no per-user web setup form.
- **HTTP self-host (multi-user)**: deploy your own instance via `docker compose up` and expose `https://<your-host>/mcp`. Per-user credentials are namespaced by JWT `sub` (TC-NearZK in-memory map). You operate the server, you set the trust boundary.
- **HTTP self-host (single-user)**: run the plugin on your own machine in HTTP mode (`--http`). The relay form on `/authorize` writes to `~/.<plugin>-mcp/config.json` per TC-Local; useful when an MCP client supports only HTTP transport.

## Migration notes (v0.x to v1.0)

If you upgraded from v0.x to v1.0:

- **stdio plugins** (wet/mnemo/crg/imagine): credentials previously in shared `~/AppData/Roaming/mcp/Config/config.enc` (Windows) or platform equivalent. v1.0 migrates to per-plugin `~/.<plugin>-mcp/config.json` on first start. The migration shim runs read-only against the old path during the v1.x release window; subsequent v1.y releases remove the shim.
- **SaaS hosted plugins** (notion/email/telegram): credentials previously persisted to disk per TC-AdminTrust. v1.0 drops disk persistence. Existing users re-OAuth on first connection to v1.0+ daemon.
