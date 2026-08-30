# Better Godot MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up better-godot-mcp.

> **Note**: Plugin install (Option 1) uses stdio mode -- no auth required for godot.
> The previous default of HTTP transport has been changed to stdio.
> If you relied on HTTP mode, set `MCP_TRANSPORT=http` or pass `--http` flag.

## Method overview

This plugin **defaults to stdio via plugin install** (`npx`). Its source tree
also provides `stdio` and `http` Docker build targets, and HTTP transport is
available for advanced self-hosting with the Godot project mounted into the
container. It does not provide an owner-hosted remote-relay/OAuth endpoint.

For comparison, the other 7 plugins in this stack (`better-notion-mcp`,
`better-email-mcp`, `better-telegram-mcp`, `wet-mcp`, `mnemo-mcp`,
`imagine-mcp`, `better-workspace-mcp`) document the same local install,
Docker-stdio, and self-hosted HTTP choices in more detail.

> **Mutually exclusive — pick one endpoint**: Do not stack `/plugin install`
> with a user `mcpServers` override for Docker stdio or HTTP. Both would load
> simultaneously, and the override would not include this plugin's skills,
> hooks, or commands. Use the default plugin install for the complete
> local-first experience.

## Option 1: Claude Code Plugin (Recommended)

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `GODOT_PATH` | Optional | Absolute path to Godot 4.x binary; auto-detect from PATH if empty |
| `GODOT_PROJECT_PATH` | Optional | Default project root (can override per tool call) |

### Steps

```bash
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-godot-mcp@n24q02m-plugins
```

This installs the server in stdio mode with skills: `/build-scene`, `/debug-issue`, `/add-mechanic`. No environment variables required -- it just works.

Optionally set `GODOT_PROJECT_PATH` to point at your Godot project; otherwise pass `project_path` per tool call.

## Environment Variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `GODOT_PROJECT_PATH` | No | -- | Default project path. Tools also accept `project_path` parameter per call. |
| `GODOT_PATH` | No | Auto-detected | Path to Godot binary. Auto-detected from PATH and common install locations. |
| `MCP_TRANSPORT` | No | `stdio` | Set to `http` to run in HTTP mode (advanced; not in scope of this guide). The `--http` CLI flag is equivalent. |
| `PORT` | No | `0` (auto) | HTTP port when `MCP_TRANSPORT=http`. Set explicitly when you need a stable port. |

## Authentication

No authentication required. This server operates on local files only.

## Verification

After setup, verify the server is working by calling the `config` tool:

```
Use the config tool with action "check" to verify the server is connected and can find Godot.
```

Expected: the tool returns Godot binary path and project status.
