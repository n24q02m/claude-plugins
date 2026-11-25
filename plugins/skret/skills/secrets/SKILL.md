---
name: secrets
description: Use skret CLI and `skret mcp` to inject, inspect, scan, sync, and manage project secrets safely across AWS SSM, GCP Secret Manager, Azure Key Vault, OCI Vault, and local YAML.
---

# skret Secrets Workflow

Always prefer `skret run -- <cmd>` or `skret mcp` instead of reading secret files directly or logging decrypted values.

## Core Commands

- Inject secrets into a process without touching disk: `skret run -- <command>`
- List secret key names only (zero decryption cost): `skret list -e <env>`
- Retrieve a single secret value programmatically: `skret get <KEY> -e <env> --plain`
- Scan tracked files and git history for leaked managed values: `skret scan --history`
- Sync secrets to GitHub Actions, GitLab, Cloudflare, dotenv, Terraform, or Kubernetes manifests: `skret sync --dry-run`
- Start the embedded MCP server (stdio default, or Streamable HTTP):
  - `skret mcp --workdir <project>`
  - `skret mcp --workdir <project> --transport http --addr 127.0.0.1:8787`

## MCP Tools & Safety Policy

- `skret_list`, `skret_env`, `skret_status`, `skret_doctor` return key names, environments, and health metadata only.
- `skret_get` is the single tool that returns a secret value.
- `skret_set`, `skret_delete`, `skret_rotate` are disabled by default; enabling them requires BOTH `mcp.allow_write: true` in `.skret.yaml` AND `"confirm": true` per tool call.
- Non-loopback `--transport http` binds require a bearer token via `--token` or `SKRET_MCP_TOKEN`.

## Local State Layout

- User credentials, sync state, and salts live under `~/.n24q02m/skret/` (or `~/.n24q02m/skret/profiles/<profile>/` when `SKRET_PROFILE` is set).
- Existing files in `~/.skret/` migrate once non-destructively on first read.
