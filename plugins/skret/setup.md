# skret -- Manual Setup Guide

`skret` (`n24q02m/skret`) is a Go CLI and embedded MCP server for managing secrets across AWS SSM Parameter Store, GCP Secret Manager, Azure Key Vault, OCI Vault, and local YAML.

## Method overview

| Method | What runs where | Best for |
|---|---|---|
| **1. Plugin install (default)** | Claude Code plugin runs `skret mcp --transport stdio` plus skills and hooks | Claude Code users |
| **2. Manual stdio** | `skret mcp --transport stdio` registered in any MCP client | Any stdio MCP client, no plugin |
| **3. Streamable HTTP** | `skret mcp --transport http --addr 127.0.0.1:8787` | Shared or remote local service |

## Prerequisites

- `skret` binary installed on `PATH`:
  - **Homebrew (macOS/Linux)**: `brew install n24q02m/tap/skret`
  - **Scoop (Windows)**: `scoop bucket add n24q02m https://github.com/n24q02m/scoop-bucket && scoop install skret`
  - **Go**: `go install github.com/n24q02m/skret/cmd/skret@latest`
- A project `.skret.yaml` initialized with `skret init` or `skret setup`.

## Method 1: Claude Code Plugin (Recommended)

The plugin runs `skret mcp --transport stdio` with zero required `userConfig` prompts; provider selection and credentials live in `.skret.yaml` and your cloud/OS keyring.

1. Open Claude Code.
2. Add the marketplace and install the plugin:
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install skret@n24q02m-plugins
   ```
3. The SessionStart hook checks whether `.skret.yaml` exists in the current workspace.
4. Keep writes disabled (default) or opt in intentionally in `.skret.yaml`:
   ```yaml
   mcp:
     allow_write: true
   ```

## Method 2: Manual stdio

```bash
claude mcp add skret -- skret mcp --transport stdio
```

For other clients (Codex, Cursor, Windsurf, VS Code, Gemini CLI, OpenCode), register command `skret` with args `["mcp", "--transport", "stdio"]`.

## Method 3: Streamable HTTP

```bash
skret mcp --workdir /path/to/project --transport http --addr 127.0.0.1:8787
```

For non-loopback binds, pass `--token` or set `SKRET_MCP_TOKEN`.
