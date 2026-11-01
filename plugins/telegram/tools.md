# Telegram MCP -- Tools Reference

better-telegram-mcp exposes Telegram (dual-mode: Bot API + MTProto) through 4 composite tools driven by an `action` parameter, plus `config` (status and runtime settings) and `help`.

## message

Send, edit, delete, forward, pin, react to, search, and read message history.

| Action | Purpose | Key parameters |
|---|---|---|
| `send` | Send a message | `chat_id`, `text` (required); `reply_to`, `parse_mode` |
| `edit` | Edit a sent message | `chat_id`, `message_id`, `text` (required); `parse_mode` |
| `delete` | Delete a message | `chat_id`, `message_id` (required) |
| `forward` | Forward a message between chats | `from_chat`, `to_chat`, `message_id` (required) |
| `pin` | Pin a message | `chat_id`, `message_id` (required) |
| `react` | React to a message with an emoji | `chat_id`, `message_id`, `emoji` (required) |
| `search` | Search messages | `query` (required); `chat_id`, `limit` (default 20) |
| `history` | Get message history for a chat | `chat_id` (required); `limit` (default 20), `offset_id` |

## chat

List, create, join, leave, and manage chats -- members, admin roles, settings, and forum topics.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List chats | `limit` (default 50) |
| `info` | Get chat info | `chat_id` (required) |
| `create` | Create a new chat | `title` (required); `is_channel` (default `false`) |
| `join` | Join a chat via link/hash | `link_or_hash` (required) |
| `leave` | Leave a chat | `chat_id` (required) |
| `members` | List chat members | `chat_id` (required); `limit` (default 50) |
| `admin` | Promote/demote a member | `chat_id`, `user_id` (required); `demote` (default `false`) |
| `settings` | Update chat title/description | `chat_id` (required); `title` or `description` (at least one) |
| `topics` | Manage forum topics | `chat_id`, `topic_action` (required); `topic_id`, `topic_name` |

## media

Send photos, files, voice, and video; download media from messages.

| Action | Purpose | Key parameters |
|---|---|---|
| `send_photo` / `send_file` / `send_voice` / `send_video` | Send a media file to a chat | `chat_id`, `file_path_or_url` (required); `caption` |
| `download` | Download media from a message | `chat_id`, `message_id` (required); `output_dir`, `file_id` |

Note: `file_id` is required in bot mode -- the Bot API cannot look up a message's media by `(chat_id, message_id)`, so get `file_id` from a message the bot already received (`message` tool results include it) and pass it to `download`. In user mode `file_id` is optional (MTProto resolves media directly from `chat_id`/`message_id`).

## contact

Manage contacts -- list, search, add, and block/unblock users (user mode only).

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List contacts | -- |
| `search` | Search contacts | `query` (required) |
| `add` | Add a contact | `phone`, `first_name` (required); `last_name` |
| `block` | Block/unblock a user | `user_id` (required); `unblock` (default `false`) |

## config

Server status and runtime settings. Credentials are never set through a tool: they come from environment variables or the local `telegram auth` command (see [setup](/servers/telegram/setup/)).

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show mode, `connected`, `authorized`, `pending_auth`, and the current config | -- |
| `set` | Update a runtime setting (`message_limit`, `timeout`) | `message_limit` or `timeout` (integer, >= 1), or generic `key` + `value` |
| `cache_clear` | Clear cached state | -- |

## help

Get full documentation for a topic.

| Parameter | Values |
|---|---|
| `topic` | `telegram` \| `messages` \| `chats` \| `media` \| `contacts` \| `all` (default) |
