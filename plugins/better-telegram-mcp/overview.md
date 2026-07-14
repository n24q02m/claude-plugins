# Better Telegram MCP -- Overview

Telegram access for AI agents in both Bot API and MTProto (user) modes -- messages, chats, media, and contacts through a small set of composite tools.

## What it does

- **Messages**: send, edit, delete, forward, pin, react, search, and read chat history.
- **Chats**: list, create, join, leave, and manage members, admin roles, settings, and forum topics.
- **Media**: send photos, files, voice, and video, and download media from a message.
- **Contacts** (user mode): list, search, add, and block/unblock users.
- Bot mode uses the Bot API; user mode uses MTProto and unlocks contact management and direct media lookup.

## Tools

Four composite tools -- `message`, `chat`, `media`, and `contact` -- driven by an `action` parameter, plus the universal `config` and `help`; `config__open_relay` reopens the browser credential form. Every action and parameter is listed in the [tools reference](/servers/better-telegram-mcp/tools/).

## Clients

Defaults to a team-shared remote deployment (`remote-relay`) and also runs over stdio for single-user local use. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and claude.ai web. See the [modes overview](/get-started/modes-overview/).

## Configuration

Bot mode needs a bot token (`TELEGRAM_BOT_TOKEN`); user mode authenticates an MTProto session through the browser relay form. Supply credentials via the relay form or environment variables, use placeholders in shared config, and never commit a real token. Full walkthrough in [setup](/servers/better-telegram-mcp/setup/).

## Next steps

- [Setup](/servers/better-telegram-mcp/setup/) -- install and configure
- [Tools reference](/servers/better-telegram-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-telegram-mcp/troubleshooting/)
