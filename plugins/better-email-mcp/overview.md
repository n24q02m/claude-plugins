# Better Email MCP -- Overview

IMAP/SMTP email for AI agents -- search, read, triage, and send across multiple accounts through a small set of composite tools.

## What it does

- **Messages**: search a mailbox, read a single email, mark read/unread, flag/unflag, move, archive, and trash.
- **Folders**: list mailbox folders per account.
- **Attachments**: list and download attachments (returned as base64).
- **Send**: compose a new email, reply, or forward, with attachments.
- Email content from external senders is wrapped in an XPIA safety marker with tag-breakout sanitisation, so the model never follows instructions hidden inside a message.

## Tools

Five composite tools -- `messages`, `folders`, `attachments`, and `send` -- driven by an `action` parameter, plus the universal `config` and `help`; `config__open_relay` reopens the browser credential form. Every action and parameter is listed in the [tools reference](/servers/better-email-mcp/tools/).

## Clients

Defaults to a team-shared remote deployment (`remote-relay`) and also runs over stdio for single-user local use. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and claude.ai web. See the [modes overview](/get-started/modes-overview/).

## Configuration

Needs IMAP/SMTP credentials for one or more accounts, supplied as `EMAIL_CREDENTIALS` via the browser relay form (or an environment variable for local use). Most providers require an app-specific password or OAuth token rather than your login password. Use placeholders in shared config and never commit real credentials. Full walkthrough in [setup](/servers/better-email-mcp/setup/).

## Next steps

- [Setup](/servers/better-email-mcp/setup/) -- install and configure
- [Tools reference](/servers/better-email-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-email-mcp/troubleshooting/)
