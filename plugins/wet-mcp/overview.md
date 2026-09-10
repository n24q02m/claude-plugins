# WET (Web Extended Toolkit) -- Overview

Web search, content extraction, media discovery, and version-aware library-docs indexing -- packaged as one MCP server so an AI agent can research the open web, read pages and local files, and pull framework documentation without leaving the conversation.

## What it does

- **Search** the web through an ordered backend chain, academic sources, and auto-indexed library documentation with project-scoped version locking.
- **Extract** clean content from URLs and local files (PDF/DOCX/PPTX/XLSX to Markdown), with batch, crawl, site-map, structured-extraction, page-interaction, and multi-step research-agent modes.
- **Media**: discover and download images, video, and audio from a page.
- Everything fetched from the open web is wrapped in an XPIA safety marker so the model treats the content as data, not instructions.

## Tools

Three multiplexed capability tools -- `search`, `extract`, and `media`, each driven by an `action` parameter -- plus the two universal tools every server in this stack ships: `config` (status, runtime settings, credential setup) and `help` (full per-tool docs). In HTTP self-host mode, `config__open_relay` reopens the browser credential form. Every action and parameter is listed in the [tools reference](/servers/wet-mcp/tools/).

## Clients

Runs over stdio with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. Self-host the HTTP build for claude.ai web compatibility and multi-user, per-user credential isolation. See the [modes overview](/get-started/modes-overview/).

## Configuration

Local retrieval needs no provider credentials. For web search, configure `SEARCH_BACKENDS`: credential-free `duckduckgo` / `startpage`, keyed `tavily` / `brave` / `exa` / `kagi`, optional-key `firecrawl`, or `searxng` with a runnable local installation or an external `SEARXNG_URL`. Upstream challenges or empty results advance to the next backend, not to an invented successful result.

- `EMBEDDING_MODELS`, `RERANK_MODELS`, `LLM_MODELS` -- optional CSV model chains for embedding, reranking, and LLM features; empty falls back to the bundled local model or disables the feature.
- Provider API keys (`JINA_AI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`) and `GITHUB_TOKEN` for a higher docs-discovery rate limit.

Use placeholders in shared config and never commit real keys. Full walkthrough in [setup](/servers/wet-mcp/setup/).

For the managed Cloudflare route, use per-subject Minimax-free completion and
paid Cohere retrieval through Cloudflare AI Gateway; see the
[provider configuration reference](/reference/relay-flow/#managed-cloudflare-model-configuration).
`DOCS_DB_BACKEND=cf-d1` disables redundant Google Drive sync and its OAuth setup
flows. This does not remove public local stdio or SearXNG support.

## Next steps

- [Setup](/servers/wet-mcp/setup/) -- install and configure
- [Tools reference](/servers/wet-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/wet-mcp/troubleshooting/)
