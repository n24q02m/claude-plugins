---
title: Plugin marketplace
description: Add the n24q02m marketplace to Claude Code and install any MCP server.
---

The `n24q02m/claude-plugins` repo is a Claude Code plugin marketplace. Adding it once gives you `/plugin install` access to all 9 MCP servers + future additions.

## Add the marketplace

```sh
/plugin marketplace add n24q02m/claude-plugins
```

## Install a server

```sh
/plugin install wet-mcp@n24q02m-plugins
/plugin install mnemo-mcp@n24q02m-plugins
/plugin install better-notion-mcp@n24q02m-plugins
# ... etc
```

After install, restart Claude Code (or reload in your IDE) so the new MCP server registers.

## List installed

```sh
/plugin
```

Select the **Installed** tab to view, enable, disable, or uninstall plugins.

## Update / remove

```sh
/plugin marketplace update n24q02m-plugins
/plugin uninstall wet-mcp@n24q02m-plugins
```

## Other MCP-compatible clients

Each server's setup page documents `mcp.json` snippets for Codex, Gemini CLI, Cursor, and Windsurf. Look under "Install" on the server's docs page (e.g. [`/servers/wet/setup/`](/servers/wet/setup/)).
