---
name: wet
description: Use the wet CLI and its HTTP MCP server for web search, content extraction, and library docs. Covers starting the server, editing ~/.wet/config.toml, hashing a token, maintaining the docs index, and warming up providers.
---

# wet -- web search, extraction, and library docs

wet is a self-hosted MCP server that speaks Streamable HTTP only (single `/mcp` endpoint, no stdio). The `wet` command is its control plane plus one thin client. This plugin provides the skill; register your instance's HTTP endpoint with `claude mcp add --transport http`.

## MCP tools

Five tools, all reached through the running server: `search`, `extract`, `media`, `config`, `help`. Call `help(tool_name=...)` for per-tool docs.

## Commands

- `wet server start [--host H] [--port P] [--foreground]` -- start the server (detached by default); `wet server stop`; `wet server status` shows pid, lock, and HTTP liveness.
- `wet config init|path|show|get|set` -- manage `~/.wet/config.toml` (auth, `[models.*]` cells, bind address). `wet config init --force` overwrites.
- `wet token hash <token>` -- print the `scrypt$...` value for `token_hash` when `auth = "token"`.
- `wet users path` -- locate the user store for `auth = "multi"`.
- `wet docs reindex <library>` / `wet docs reembed` / `wet docs import` -- maintain the docs index; no running server needed.
- `wet search <query> [--max-results N] [--url URL] [--token TOKEN]` -- search through the running server (token defaults to `WET_TOKEN`).
- `wet warmup` -- probe the configured providers and pre-download enabled local resources.
- `wet -V` -- print the version.

## Notes

- Python 3.13 is required. Run without installing via `uvx --python 3.13 --from wet-mcp wet <command>`.
- Auth modes: `no-auth` (loopback only), `token`, `multi`. Clients send the plaintext token as `Authorization: Bearer <token>`; the server stores only the hash.
- State lives under `~/.wet/` (config, `docs.db`, cache, downloads).
- Search chain and browser backends are server-host environment variables (`SEARCH_BACKENDS`, `BROWSER_BACKENDS`); see the setup page for the full list.
