# Better Email MCP -- Overview

IMAP/SMTP email for AI agents -- search, read, triage, and send across multiple accounts through a small set of composite tools.

## What it does

- **Messages**: search a mailbox, read a single email, mark read/unread, flag/unflag, move, archive, trash, compose, reply, and forward.
- **Folders**: list mailbox folders, or read targeted status metadata (`messages`, `unseen`, `uid_next`) for one exact account and folder.
- **Attachments**: list and download attachments (returned as base64).
- Email content from external senders is wrapped in an XPIA safety marker with tag-breakout sanitisation, so the model never follows instructions hidden inside a message.

## Tools

Four action-driven tools -- `messages`, `folders`, `attachments`, and `config` -- plus `config__open_relay` and `help`; `config__open_relay` reopens the browser credential form. Every action and parameter is listed in the [tools reference](/servers/better-email-mcp/tools/).

## Clients

Defaults to local `stdio` through the marketplace plugin. `remote-relay` remains available for explicit HTTP deployments. Works with Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and HTTP-capable web clients. See the [modes overview](/get-started/modes-overview/).

## Configuration

Needs IMAP/SMTP credentials for one or more accounts, supplied as `EMAIL_CREDENTIALS` via the browser relay form (or an environment variable for local use). Most providers require an app-specific password or OAuth token rather than your login password. Use placeholders in shared config and never commit real credentials. Full walkthrough in [setup](/servers/better-email-mcp/setup/).

## Next steps

- [Setup](/servers/better-email-mcp/setup/) -- install and configure
- [Tools reference](/servers/better-email-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-email-mcp/troubleshooting/)
