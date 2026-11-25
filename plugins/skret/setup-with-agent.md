# skret -- Agent Setup Guide

> Give this file to your AI agent to set up `skret` cleanly.

## Method overview

`skret` runs locally over `stdio` by default (`skret mcp --transport stdio`). There are no `userConfig` secrets to pass into plugin configuration; `.skret.yaml` selects the provider (`local`, `aws`, `gcp`, `azure`, `oci`) and environment (`dev`, `prod`, etc.).

## Option 1: Claude Code Plugin (Recommended)

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install skret@n24q02m-plugins
```

Verify `.skret.yaml` exists in the target repository (or initialize one with `skret init --provider=local`).

## Environment Variables & Security Policy

- `SKRET_PROFILE`: selects an isolated profile directory under `~/.n24q02m/skret/profiles/<profile>/`.
- `SKRET_MCP_TOKEN`: bearer token required when running `skret mcp --transport http` on a non-loopback address.
- Mutation tools (`skret_set`, `skret_delete`, `skret_rotate`) are disabled unless BOTH `mcp.allow_write: true` is set in `.skret.yaml` AND `"confirm": true` is passed on the call.

## Verification

1. Call `skret_status` (or `skret_doctor`) to inspect resolved environment, provider, config file path, and write policy without network calls.
2. Call `skret_list` to verify key names are readable.
