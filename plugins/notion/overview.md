# Notion MCP -- Overview

Markdown-first access to a Notion workspace for AI agents. Read and write pages and databases as Markdown instead of wrestling with raw Notion block JSON, with roughly 95% API coverage in a curated composite tool set.

## What it does

- **Pages and databases**: create, read, update, move, archive, restore, and duplicate pages; create and query databases and bulk-edit rows.
- **Blocks**: read and modify block-level content within a page.
- **Users, workspace, comments, file uploads**: list users, search the workspace, manage comments, and upload files.
- **Conversion**: translate between Markdown and Notion block JSON in either direction.
- Content read from the workspace is wrapped in an XPIA safety marker so the model treats page and comment text as data, not instructions.

## Tools

Eight composite tools -- `pages`, `databases`, `blocks`, `users`, `workspace`, `comments`, `file_uploads`, and `content_convert` -- plus the universal `config` (credential state) and `help`. Every action and parameter is listed in the [tools reference](/servers/notion/tools/).

## Deployment

Defaults to `stdio` for single-user local use, and also runs as a self-hosted HTTP service behind bearer-token auth. There is no endpoint hosted by the author: for HTTP you run the server yourself and point your MCP client at it. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. See the [modes overview](/get-started/modes-overview/).

## Configuration

Needs a Notion integration token (`NOTION_TOKEN`, starts with `ntn_`). Supply it through the plugin's `NOTION_TOKEN` field or an environment variable, or store it once with `notion auth` (saved under `~/.better-notion/`). In HTTP `multi` mode each user gets their own token, stored with `notion auth --user <namespace>` on the server host. The integration must be shared with each page or database you want the agent to reach. Use a placeholder in shared config and never commit a real token. Full walkthrough in [setup](/servers/notion/setup/).

## Next steps

- [Setup](/servers/notion/setup/) -- install and configure
- [Tools reference](/servers/notion/tools/) -- every action and parameter
- [Troubleshooting](/servers/notion/troubleshooting/)
