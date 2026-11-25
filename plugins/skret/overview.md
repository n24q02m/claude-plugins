# skret -- Overview

Cloud-provider secret manager CLI and embedded MCP server (`n24q02m/skret`) for AWS SSM Parameter Store, GCP Secret Manager, Azure Key Vault, OCI Vault, and local age-encrypted YAML.

## What it does

- **Inject at runtime**: `skret run -- <command>` injects resolved secrets as environment variables without writing `.env` files to disk.
- **Read and discover**: `skret_list` and `skret_env` list key names and environments with zero decryption cost; `skret_get` reads a single secret value.
- **Write gating**: mutation tools (`skret_set`, `skret_delete`, `skret_rotate`) are disabled by default and require both `mcp.allow_write: true` in `.skret.yaml` and a per-call `"confirm": true` flag.
- **Health and leak protection**: `skret_status` / `skret_doctor` inspect resolved provider, environment, and write policy without making network calls; the CLI provides `skret scan` and `skret audit`.

## Tools

Eight MCP tools: read/health tools `skret_list`, `skret_get`, `skret_env`, `skret_status`, `skret_doctor`, plus write-gated tools `skret_set`, `skret_delete`, `skret_rotate`. Full schemas in [tools reference](/servers/skret/tools/).

## Clients

`skret` defaults to local `stdio` (`skret mcp --transport stdio`) as a child process of Claude Code or any MCP client. It also supports Streamable HTTP (`skret mcp --transport http`) with bearer token enforcement on non-loopback binds (`--token` or `SKRET_MCP_TOKEN`).

## Next steps

- [Setup](/servers/skret/setup/) -- install `skret` and configure `.skret.yaml`
- [Tools reference](/servers/skret/tools/) -- every MCP tool and parameter
- [Troubleshooting](/servers/skret/troubleshooting/) -- common issues and remediation
