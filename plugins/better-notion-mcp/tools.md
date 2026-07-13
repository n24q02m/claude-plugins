# Better Notion MCP -- Tools Reference

better-notion-mcp exposes the Notion API through 8 composite tools, each driven by an `action` parameter, plus `config` (credential setup), `config__open_relay`, and `help`. The 7 tools that read live workspace content (`pages`, `databases`, `blocks`, `users`, `workspace`, `comments`, `file_uploads`) wrap their results in an XPIA safety marker -- boundary tags plus an instruction to treat the content as data, not commands -- since Notion pages/comments can contain arbitrary user- or third-party-authored text. `content_convert`, `config`, `help`, and `config__open_relay` are not wrapped.

## pages

Page CRUD for individual pages and database rows. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `create` | Create a new page | `parent_id`, `title` (required); `content`, `properties`, `icon`, `cover` |
| `get` | Get a page as markdown | `page_id` (required) |
| `get_property` | Get one property's value | `page_id`, `property_id` (required) |
| `update` | Update a page | `page_id` (required); `title`, `content`, `append_content`, `properties`, `icon`, `cover`, `archived`, `replace` (default `false` = append, not overwrite) |
| `move` | Move a page to a new parent | `page_id`, `parent_id` (required) |
| `archive` / `restore` | Archive or restore one or more pages (batched) | `page_id` or `page_ids` (required) |
| `duplicate` | Duplicate one or more pages (batched) | `page_id` or `page_ids` (required) |

## databases

Database schema, query, and bulk row operations. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `create` | Create a new database | `parent_id`, `title`, `properties` (required); `is_inline`, `icon`, `cover` |
| `get` | Get database schema | `database_id` (required) |
| `query` | Query rows | `database_id` (required); `filters`, `sorts`, `limit`, `search` (auto-builds an OR rich-text filter) |
| `create_page` | Create one or more rows | `database_id` (required); `pages[]` or `page_properties` |
| `update_page` | Update one or more rows | `pages[]` or `page_id` + `page_properties` |
| `delete_page` | Archive (not hard-delete) one or more rows | `page_id` / `page_ids` / `pages` |
| `create_data_source` | Create a data source on a database | `database_id`, `title`, `properties` (required) |
| `update_data_source` | Update a data source | `data_source_id` (required) |
| `update_database` | Update database metadata | `database_id` (required); `parent_id`, `title`, `description`, `is_inline`, `icon`, `cover` |
| `list_templates` | List page templates on a database | `database_id` (required) |

## blocks

Read and modify block-level content within pages. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `get` | Get a block | `block_id` (required) |
| `children` | List child blocks (auto-paginated, deep for tables/toggles/columns) | `block_id` (required) |
| `append` | Append content to a block's children | `block_id`, `content` (required); `position` (`start`\|`end`[default]\|`after_block`), `after_block_id` |
| `update` | Update a block's content (paragraph/heading/list-item/quote/to_do/code only) | `block_id`, `content` (required) |
| `delete` | Delete a block | `block_id` (required) |

## users

Get user information. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List workspace users | `limit` |
| `get` | Get a specific user | `user_id` (required) |
| `me` | Get the bot's own identity | -- |
| `from_workspace` | Extract users from page `created_by`/`last_edited_by` metadata (fallback when `list` hits a restricted-resource error) | `limit` (default scans 500 pages) |

## workspace

Search the workspace and get workspace info. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `info` | Get bot identity / workspace info (cached 5 min) | -- |
| `search` | Search pages and data sources | `query` (empty = all); `filter.object` (`page`\|`data_source`), `sort`, `limit` |

## comments

Manage page comments. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | List comments on a page | `page_id` (required) |
| `get` | Get a specific comment | `comment_id` (required) |
| `create` | Create a comment | `content` (required); `page_id` XOR `discussion_id` (required) |

## file_uploads

Upload files to Notion (max 10 MB per part). Wrapped as external content -- attachment metadata is treated as untrusted.

| Action | Purpose | Key parameters |
|---|---|---|
| `create` | Start a file upload | `filename`, `content_type` (required); `mode` (`single`[default]\|`multi_part`), `number_of_parts` |
| `send` | Send file content (base64) | `file_upload_id`, `file_content` (required); `part_number` |
| `complete` | Finalize a multi-part upload | `file_upload_id` (required) |
| `retrieve` | Get a file upload's status | `file_upload_id` (required) |
| `list` | List file uploads | `limit` |

## content_convert

Convert between Markdown and Notion block JSON. No `action` parameter -- uses `direction` instead. Not wrapped as external content.

| Direction | Purpose | Key parameters |
|---|---|---|
| `markdown-to-blocks` | Convert Markdown text to Notion block JSON | `content` (string) |
| `blocks-to-markdown` | Convert Notion block JSON to Markdown | `content` (string or array, JSON-parsed if a string) |

## config

Manage server configuration and credential state. Not wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show credential state, token presence, setup URL, token source | -- |
| `setup_start` | Start credential relay setup | `force` |
| `setup_reset` | Clear saved credential state | -- |
| `setup_complete` | Re-resolve credential state | -- |
| `set` | No-op -- Notion has no mutable runtime settings | `key`, `value` |
| `cache_clear` | No-op (nothing to clear) | -- |

## help

Get full documentation for a tool.

| Parameter | Values |
|---|---|
| `tool_name` | `pages` \| `databases` \| `blocks` \| `users` \| `workspace` \| `comments` \| `file_uploads` \| `content_convert` |

## config__open_relay

Opens the relay configuration form in the user's browser. No parameters.
