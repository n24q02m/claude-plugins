# Email MCP -- Overview

IMAP/SMTP email for AI agents -- search, read, triage, and send across multiple accounts through a small set of composite tools.

## What it does

- **Messages**: search a mailbox, read a single email, mark read/unread, flag/unflag, move, archive, trash, compose, reply, and forward.
- **Folders**: list mailbox folders, or read targeted status metadata (`messages`, `unseen`, `uid_next`) for one exact account and folder.
- **Attachments**: list and download attachments (returned as base64).
- Email content from external senders is wrapped in an XPIA safety marker with tag-breakout sanitisation, so the model never follows instructions hidden inside a message.

## Tools

Four action-driven tools -- `messages`, `folders`, `attachments`, and `config` -- plus `help`. `config` reports credential state and how to fix it; there is no browser setup form. Every action and parameter is listed in the [tools reference](/servers/email/tools/).

## Clients

Runs over stdio by default (single user, credentials from environment variables) and can run as a single-user HTTP server for self-hosting. There is no hosted public instance. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and claude.ai web for a self-hosted HTTP server.

## Configuration

Needs IMAP/SMTP credentials for one or more accounts, supplied as `EMAIL_CREDENTIALS` (or `EMAIL_USER` + `EMAIL_APP_PASSWORD`) in the server environment. Most providers require an app-specific password rather than your login password. Outlook/Hotmail/Live accounts can instead sign in once with `email auth outlook <address>` (OAuth device code). Use placeholders in shared config and never commit real credentials. Full walkthrough in [setup](/servers/email/setup/).

## Next steps

- [Setup](/servers/email/setup/) -- install and configure
- [Tools reference](/servers/email/tools/) -- every action and parameter
- [Troubleshooting](/servers/email/troubleshooting/)
