# Better Workspace MCP -- Overview

Google Workspace for AI agents -- read and write Docs, Drive, Calendar, Gmail, Sheets, Slides, Tasks, Chat, People, and Forms through one composite tool per domain, across several Google accounts.

## What it does

- **Docs**: read document text, create documents, insert and replace text, apply formatting, read pending suggestions.
- **Drive**: search files, create and find folders, move, rename, trash, download, and read comments.
- **Calendar**: list calendars and events, create, update, delete, respond to invites, and find free time.
- **Gmail**: search, read, send, draft, modify labels on messages and threads, download attachments.
- **Sheets**: read a sheet, a range, or its metadata (read-only).
- **Slides**: 19 actions across deck structure, text, shapes, images, tables, and speaker notes.
- **Tasks, Chat, People, Forms**: task lists and tasks; spaces, threads, and DMs; profile lookups; form creation, questions, and responses.
- **Time**: local date, time, and timezone helpers that need no Google account.

## Tools

Eleven composite tools -- `docs`, `drive`, `calendar`, `gmail`, `sheets`, `slides`, `tasks`, `chat`, `people`, `forms`, and `time` -- each driven by an `action` parameter, plus the universal `config` (credential state and account management) and `help`. Every action and parameter is listed in the [tools reference](/servers/better-workspace-mcp/tools/).

## Multi-account

Every domain tool takes an `account` parameter -- the email of the Google account the call acts as. Omit it and the call runs against the primary account. Accounts are added, listed, removed, and re-prioritised through `config`. Naming an account that is not configured is an error that says so; the call is never quietly rerouted to the primary, because a silent fallback would act on the wrong mailbox or drive.

## Clients

Defaults to `stdio` for single-user local use, and also runs as a self-hosted multi-user HTTP service where each user's Google credentials sit in their own bucket keyed by their JWT `sub`. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. See the [modes overview](/get-started/modes-overview/).

There is no n24q02m-hosted instance of this server; HTTP mode is self-host only.

## Configuration

Needs a Google OAuth client you create yourself, supplied as `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` -- **Desktop app** type for stdio, **Web application** type for HTTP. The server ships no Google client of its own, so the consent screen and the API quota belong to your project. The first run opens Google's consent screen once; the refresh token is then stored encrypted. Use placeholders in shared config and never commit real credentials. Full walkthrough in [setup](/servers/better-workspace-mcp/setup/).

## Status and license

Still pre-1.0 -- published as `0.1.0-beta.x` on npm and `:beta` on the registries, with no stable tag yet.

Unlike the rest of the stack, this server is **Apache-2.0**, not MIT: it vendors Apache-2.0 code from [gemini-cli-extensions/workspace](https://github.com/gemini-cli-extensions/workspace) and carries that license across the repo.

## Next steps

- [Setup](/servers/better-workspace-mcp/setup/) -- install and configure
- [Tools reference](/servers/better-workspace-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-workspace-mcp/troubleshooting/)
