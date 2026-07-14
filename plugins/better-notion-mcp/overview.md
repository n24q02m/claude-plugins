# Better Notion MCP -- Overview

Markdown-first access to a Notion workspace for AI agents. Read and write pages and databases as Markdown instead of wrestling with raw Notion block JSON, with roughly 95% API coverage in a curated composite tool set.

## What it does

- **Pages and databases**: create, read, update, move, archive, restore, and duplicate pages; create and query databases and bulk-edit rows.
- **Blocks**: read and modify block-level content within a page.
- **Users, workspace, comments, file uploads**: list users, search the workspace, manage comments, and upload files.
- **Conversion**: translate between Markdown and Notion block JSON in either direction.
- Content read from the workspace is wrapped in an XPIA safety marker so the model treats page and comment text as data, not instructions.

## Tools

Eight composite tools -- `pages`, `databases`, `blocks`, `users`, `workspace`, `comments`, `file_uploads`, and `content_convert` -- plus the universal `config` and `help`; `config__open_relay` reopens the browser credential form. Every action and parameter is listed in the [tools reference](/servers/better-notion-mcp/tools/).

## Clients

Defaults to a team-shared remote deployment (`remote-oauth`) and also runs over stdio for single-user local use. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and claude.ai web. See the [modes overview](/get-started/modes-overview/).

## Configuration

Needs a Notion integration token (`NOTION_TOKEN`), supplied via the browser relay form or an environment variable. The integration must be shared with each page or database you want the agent to reach. Use a placeholder in shared config and never commit a real token. Full walkthrough in [setup](/servers/better-notion-mcp/setup/).

## Next steps

- [Setup](/servers/better-notion-mcp/setup/) -- install and configure
- [Tools reference](/servers/better-notion-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-notion-mcp/troubleshooting/)
