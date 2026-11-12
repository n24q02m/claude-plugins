---
name: wet
description: Vận hành wet — MCP server HTTP-only (Streamable HTTP) qua CLI control plane `wet`: start/stop/status server, fetch docs web & library docs (web scraping, library-docs, crawl4ai, searxng), warmup cache. Không có stdio mode, không có auth/logout.
---

# wet — HTTP MCP server + control-plane CLI

wet là MCP server HTTP-only: `wet server start` phục vụ Streamable HTTP tại
`http://127.0.0.1:8000/mcp`. CLI `wet` là control plane cộng một consumer mỏng. Chạy `wet`
không subcommand chỉ in usage (rc 0) — không có passthrough stdio, không có `--http`, và
client không tự spawn wet như subprocess.

## Lệnh chính
- `wet --help` — xem toàn bộ subcommands; `wet -V` — in phiên bản
- `wet server start|stop|status` — vòng đời server HTTP (`start`: detached, `--foreground` để giữ tiến trình; `status`: pid/lock/HTTP liveness)
- `wet config init|path|show|get|set` — cấu hình `~/.wet/config.toml` (`get`/`set` dùng key dạng `server.port`)
- `wet token hash <token>` — in scrypt hash để dán vào `users.toml`
- `wet users path` — in đường dẫn `users.toml`
- `wet docs list|reindex|import|reembed` — bảo trì docs store, chạy trực tiếp trên SQLite (không cần server)
- `wet search "<query>"` — gọi server đang chạy qua MCP; server down thì in hint và exit 2
- `wet warmup` — pre-download model + auto-setup (SearXNG, browser) để tránh chậm lần đầu

## Ghi chú
- Repo + CLI: `wet`; distribution PyPI là `n24q02m-wet` (`uvx --from n24q02m-wet wet …`). Console scripts: `n24q02m-wet`, `wet`, `wet-mcp` (legacy alias) — cả ba chạy cùng một CLI.
- Data/config dir: `~/.wet` (`config.toml`, `docs.db`, cache).
- Lệnh auth/logout/doctor không tồn tại trong CLI: kiểm tra sức khoẻ server bằng `wet server status`, kiểm tra provider bằng `wet warmup`. Google Drive sync thuộc về better-drive, không thuộc wet.
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

- Python 3.13 is required. Run without installing via `uvx --python 3.13 --from n24q02m-wet wet <command>`.
- Auth modes: `no-auth` (loopback only), `token`, `multi`. Clients send the plaintext token as `Authorization: Bearer <token>`; the server stores only the hash.
- State lives under `~/.wet/` (config, `docs.db`, cache, downloads).
- Search chain and browser backends are server-host environment variables (`SEARCH_BACKENDS`, `BROWSER_BACKENDS`); see the setup page for the full list.
