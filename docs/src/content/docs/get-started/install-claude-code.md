---
title: Install Claude Code
description: Install the Claude Code CLI prerequisite for the MCP server stack.
---

The MCP server stack ships as Claude Code plugins. Other MCP-compatible clients (Codex, Gemini CLI, Cursor, Windsurf) work too — those instructions live in each server's setup page.

## Install

Pick one:

```sh
# macOS / Linux
curl -fsSL https://claude.ai/install.sh | sh

# Windows (scoop)
scoop install claude-code

# Windows (winget)
winget install Anthropic.ClaudeCode
```

## Authenticate

```sh
claude auth login
```

## Verify

```sh
claude --version
```

If `claude` is on your PATH and reports a version, you're set. Continue to [plugin marketplace](/get-started/plugin-marketplace/).
