# WET (Web Extended Toolkit) -- Overview

wet is an open-source, self-hosted MCP server for AI agents: web search, content extraction, and library documentation lookup. It runs as a single HTTP process on a machine you control and exposes five tools to any MCP client.

## What it does

- **Search** -- web search through a configurable backend chain (SearXNG, keyed providers, or credential-free DuckDuckGo/Startpage), academic search, and library documentation search with a local, version-aware docs index.
- **Extract** -- clean content from URLs (single, batch, crawl, site map), local file conversion (PDF, DOCX, PPTX, XLSX, and more), LLM-backed structured extraction, page interaction, and change tracking between fetches.
- **Media** -- list and download images, videos, and audio from a page.
- **Config** -- inspect status, change a few runtime settings, clear the cache, re-index a library, and warm up local resources.

Results from `search`, `extract`, and `media` carry an XPIA safety marker because they return externally fetched web content.

## Tools

Five tools: `search`, `extract`, `media`, `config`, `help`. See the [tools reference](/servers/wet/tools/).

## Deployment

wet speaks **Streamable HTTP only** on a single `/mcp` endpoint. There is no stdio transport and no hosted public instance: you run one instance and point MCP clients at it.

- **Local**: `uvx --python 3.13 --from wet-mcp wet server start` runs a loopback `no-auth` instance on `http://127.0.0.1:8000/mcp`.
- **docker compose**: build from the source repo and publish on loopback with token auth.
- **Your own host**: run the instance behind a TLS proxy you control and use `auth = "token"` or `"multi"`.

Clients: Claude Code (with the plugin, or `claude mcp add --transport http`), Codex, Gemini CLI, Cursor, Windsurf, and claude.ai web for a remote instance. The Claude Code plugin adds the wet skill; its bundled stdio MCP entry cannot connect to wet 3.20.0 (HTTP-only), so register your instance with `claude mcp add --transport http`.

## Configuration

Auth, bind address, and provider settings live in the host-owned `~/.wet/config.toml` (create it with `wet config init`). Embedding, reranking, and LLM tasks use independent `[models.*]` cells over OpenAI-compatible HTTP; with no embed/rerank cell, wet falls back to local ONNX models. Search and browser backends are chosen with environment variables on the server host. MCP clients never see this file.

## Next steps

- [Setup](/servers/wet/setup/) -- start an instance and register it with a client
- [Tools reference](/servers/wet/tools/) -- every tool and action
- [Troubleshooting](/servers/wet/troubleshooting/) -- common problems
