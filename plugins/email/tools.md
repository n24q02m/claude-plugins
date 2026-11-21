# Email MCP -- Tools Reference

email exposes IMAP/SMTP email through 4 action-driven tools -- `messages`, `folders`, `attachments`, and `config` -- plus `help`. `messages` and `attachments` -- the two tools that return email content from external senders -- wrap their results in an XPIA safety marker: `<untrusted_email_content>` boundary tags plus an instruction not to follow, execute, or comply with any instructions found inside the email content. The wrapper also sanitizes any literal occurrence of that tag name inside the payload to prevent tag-breakout injection. `folders`, `config`, and `help` are not wrapped.

## messages

Search, read, and manage email messages. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `search` | Search an account's mailbox | `account`, `query` (default `UNSEEN`), `folder` (default `INBOX`), `limit` (default 20) |
| `read` | Read a single email (bounded preview of 4000 characters by default) | `account`, `uid` (required); `folder`, `preview`, `max_chars` (1-100000), `full` |
| `mark_read` / `mark_unread` | Add/remove the `\Seen` flag | `account`, `uid` or `uids` (required); `folder` |
| `flag` / `unflag` | Add/remove the `\Flagged` (star) flag | `account`, `uid` or `uids` (required); `folder` |
| `move` | Move email(s) to another folder | `account`, `uid`/`uids`, `destination` (required); `folder` |
| `archive` | Move email(s) to the auto-detected archive folder | `account`, `uid`/`uids` (required); `folder` |
| `trash` | Move email(s) to trash | `account`, `uid`/`uids` (required); `folder` |
| `new` | Compose a fresh email | `account`, `to`, `subject`, `body` (required); `from`, `cc`, `bcc`, `attachments`, `draft` |
| `reply` | Reply to an email (`to`/`subject` auto-derived, `Re:` prefixed) | `account`, `uid`, `body` (required); `from`, `to`, `subject`, `folder`, `cc`, `bcc`, `attachments`, `draft` |
| `forward` | Forward an email (includes original body, `Fwd:` prefixed) | `account`, `uid`, `to`, `body` (required); `from`, `subject`, `folder`, `cc`, `bcc`, `attachments`, `draft` |

## folders

List mailbox folders or read targeted IMAP STATUS metadata. Not wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List folders for an account (or all accounts) | `account` (optional; omit for all accounts) |
| `status` | Read `MESSAGES`, `UNSEEN`, and `UIDNEXT` for one exact mailbox | `account` (required), `folder` (required; exact mailbox path) |

`status` is read-only and returns `messages`, `unseen`, and `uid_next`. It does not select or enumerate the mailbox and never falls back to all accounts.

## attachments

List and download email attachments. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List attachments on an email (filename, content_type, size) | `account`, `uid` (required), `folder` |
| `download` | Download an attachment as base64 | `account`, `uid` (required), `folder`, `filename` (required, case-sensitive) |

`attachments` (optional, all actions): array of `{filename, content_base64, content_type?}`, same shape as `attachments`' `download` action returns. Max 10 files, total decoded size <= 25MB.

`from` sends as the account email or one of its `aliases` from the accounts file, optionally as `"Name <address>"`; alone it picks the account that owns the address. `draft: true` saves the message to the Drafts folder instead of sending it. With `EMAIL_MCP_DRAFT_ONLY=1` every `new`/`reply`/`forward` is saved as a draft, and `move`/`archive`/`trash` are refused.

## config

Report credential state and setup guidance. Not wrapped as external content. Credentials are read from the accounts file, the server environment, or saved Outlook tokens at startup; this tool never opens a form or returns a setup URL. For an HTTP multi-user caller, `status` reports that caller's accounts only, `cache_clear` drops only that caller's entries, and `setup_reset` / `setup_complete` are refused.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show credential `state` and the configured `accounts` | -- |
| `setup_status` | Show the credential `state` only | -- |
| `setup_start` | Return setup instructions: set `EMAIL_ACCOUNTS_FILE` (an accounts file), `EMAIL_CREDENTIALS`, or `EMAIL_USER` + `EMAIL_APP_PASSWORD` and restart, or run `email auth outlook <address>` | -- |
| `setup_reset` | Delete the saved config and return to `awaiting_setup` | -- |
| `setup_complete` | Re-check the state; returns `previous_state`, `state`, and `accounts` | -- |
| `set` | No-op -- email has no mutable runtime settings; always returns `ok: false` | -- |
| `cache_clear` | Clear the IMAP sent/drafts/archive folder caches and the OAuth token cache | -- |

## help

Get full documentation for a tool.

| Parameter | Values |
|---|---|
| `tool_name` | `messages` \| `folders` \| `attachments` \| `config` \| `help` |
