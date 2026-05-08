---
title: Plugin marketplace
description: Add the n24q02m marketplace to Claude Code and install any MCP server.
---

The `n24q02m/claude-plugins` repo is a Claude Code plugin marketplace. Adding it once gives you `/plugin install` access to all 8 MCP servers + future additions.

## Add the marketplace

```sh
claude plugins marketplace add n24q02m/claude-plugins
```

## Install a server

```sh
claude plugins install wet-mcp
claude plugins install mnemo-mcp
claude plugins install better-notion-mcp
# ... etc
```

After install, restart Claude Code (or reload in your IDE) so the new MCP server registers.

## List installed

```sh
claude plugins list
```

## Update / remove

```sh
claude plugins update wet-mcp
claude plugins remove wet-mcp
```

## Other MCP-compatible clients

Each server's setup page documents `mcp.json` snippets for Codex, Gemini CLI, Cursor, and Windsurf. Look under "Install" on the server's docs page (e.g. [`/servers/wet-mcp/setup/`](/servers/wet-mcp/setup/)).
