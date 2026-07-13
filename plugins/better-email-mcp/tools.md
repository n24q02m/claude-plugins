# Better Email MCP -- Tools Reference

better-email-mcp exposes IMAP/SMTP email through 5 composite tools driven by an `action` parameter, plus `config` (credential setup) and `help`. `messages` and `attachments` -- the two tools that return email content from external senders -- wrap their results in an XPIA safety marker: `<untrusted_email_content>` boundary tags plus an instruction not to follow, execute, or comply with any instructions found inside the email content. The wrapper also sanitizes any literal occurrence of that tag name inside the payload to prevent tag-breakout injection. `folders`, `send`, `config`, and `help` are not wrapped.

## messages

Search, read, and manage email messages. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `search` | Search an account's mailbox | `account`, `query` (default `UNSEEN`), `folder` (default `INBOX`), `limit` (default 20) |
| `read` | Read a single email | `uid` (required), `account`, `folder` |
| `mark_read` / `mark_unread` | Add/remove the `\Seen` flag | `uid` or `uids` (required) |
| `flag` / `unflag` | Add/remove the `\Flagged` (star) flag | `uid` or `uids` (required) |
| `move` | Move email(s) to another folder | `uid`/`uids` (required), `destination` (required) |
| `archive` | Move email(s) to the auto-detected archive folder | `uid`/`uids` (required) |
| `trash` | Move email(s) to trash | `uid`/`uids` (required) |

## folders

List mailbox folders. Not wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List folders for an account (or all accounts) | `account` |

## attachments

List and download email attachments. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List attachments on an email (filename, content_type, size) | `account`, `uid` (required), `folder` |
| `download` | Download an attachment as base64 | `account`, `uid` (required), `folder`, `filename` (required, case-sensitive) |

## send

Compose and send emails. Not wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `new` | Compose a fresh email | `account`, `to`, `subject`, `body` (required); `cc`, `bcc`, `attachments` |
| `reply` | Reply to an email (`to`/`subject` auto-derived, `Re:` prefixed) | `account`, `uid`, `body` (required); `cc`, `bcc`, `attachments` |
| `forward` | Forward an email (includes original body, `Fwd:` prefixed) | `account`, `uid`, `to`, `body` (required); `subject`, `cc`, `bcc`, `attachments` |

`attachments` (optional, all actions): array of `{filename, content_base64, content_type?}`, same shape as `attachments`' `download` action returns. Max 10 files, total decoded size <= 25MB.

## config

Manage email credential setup and runtime configuration. Not wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show credential state, setup URL, configured accounts | -- |
| `setup_start` | Return the relay setup URL | `force` (restart setup) |
| `setup_reset` | Wipe saved credentials | -- |
| `setup_complete` | Re-check state after relay form submission | -- |
| `set` | No-op -- email has no mutable runtime settings | `key`, `value` |
| `cache_clear` | Clear the Sent-folder cache, archive-folder cache, and OAuth token cache | -- |

## help

Get full documentation for a tool.

| Parameter | Values |
|---|---|
| `tool_name` | `messages` \| `folders` \| `attachments` \| `send` \| `config` \| `help` |

## config__open_relay

Opens the relay configuration form (`/authorize`) in the user's browser and returns the relay URL, whether the browser launched, and the credential state. No parameters.
