# WET (Web Extended Toolkit) -- Tools Reference

wet-mcp exposes 5 tools: 3 multiplexed capability tools (`search`, `extract`, `media`), each driven by an `action` parameter, plus `config` (server management) and `help` (full per-tool docs). Results from `search`, `extract`, and `media` are wrapped in an XPIA safety marker -- boundary tags plus an instruction to treat the content as data, not commands -- since they return externally-fetched web content.

## search

Find information across the web, academic sources, X/Twitter, or indexed library documentation. Returns result listings (titles, URLs, snippets) -- not full page content. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `search` | Web search via SearXNG | `query` (required), `categories`, `max_results`, `time_range`, `include_domains`/`exclude_domains`, `expand` (LLM query expansion), `enrich` (fetch real snippets) |
| `research` | Academic/scientific search (Google Scholar, arXiv, PubMed) | `query` (required), `max_results`, `time_range` |
| `x` | X/Twitter search via xAI. Returns a **synthesized answer with citations**, not a link list -- X blocks direct extraction. Bills per query; requires `XAI_API_KEY` | `query` (required), `handles`/`exclude_handles` (up to 20 handles, mutually exclusive), `time_range`, `from_date`/`to_date` (ISO8601, override `time_range`), `video` (enable video understanding of linked media) |
| `docs` | Search library documentation, auto-indexing on first query | `library` (required), `query` (required), `language`, `version` |
| `docs_resolve` | Free-form library name -> ranked `library_id` list | `query` (library name, required) |
| `docs_query` | Version-aware docs query honoring a project's locked library set + token cap | `library` (required), `query` (required), `version`, `topic`, `project_path`, `limit` |
| `docs_lock_project` | Detect project manifests (pyproject/package.json/go.mod/Cargo.toml) and lock the library set for isolation (Cabinets) | `project_path` (required) |
| `similar` | Find pages similar to a URL | `query` = full URL (required), `max_results` |

## extract

Read and return full page content from URLs or local files. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `extract` | Get clean content from URLs (markdown/text/html) | `urls` (required, max 20), `format`, `stealth` (anti-bot bypass) |
| `batch` | Batch extract with per-domain rate limiting | `urls` (required, max 50) |
| `crawl` | Deep crawl following links from root URLs | `urls` (required), `depth` (default 2, max 5), `max_pages` (default 20, max 100) |
| `map` | Discover site URL structure without extracting content | `urls` (required), `depth`, `max_pages` |
| `convert` | Convert local files (PDF, DOCX, PPTX, XLSX) to Markdown | `paths` (required) |
| `extract_structured` | Extract structured data from a page using a JSON Schema + LLM | `urls` (required), `schema` (required JSON Schema dict), `prompt` |
| `agent` | Multi-step research orchestration: search the web, extract top results, synthesize a cited Markdown answer | `query` (required), `max_urls` (default 5, hard cap 20), `synthesis_model`, `token_budget` (default 10000) |
| `interact` | Drive a page with click/fill/submit via a browser automation session | `url` (required), `actions` (required list of `{type, selector?, description?, value?}`), `session` (persistent session id), `screenshot` |

## media

Discover and download media files (images, videos, audio) from web pages. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | Scan a page and return media URLs with metadata | `url` (required), `media_type` (`images`\|`videos`\|`audio`\|`files`\|`all`), `max_items` |
| `download` | Download media files to local storage | `media_urls` (required), `output_dir` (must resolve within the configured download directory) |

Vision/audio/video analysis of downloaded media lives in imagine-mcp's `understand` tool, not here.

## config

Server configuration and management, not wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show current config, database, embedding/reranker backend, cache, and sync status | -- |
| `set` | Update a runtime setting (`log_level`, `tool_timeout`, `wet_cache`, `sync_enabled`, `sync_folder`, `sync_interval`) | `key`, `value` (required) |
| `cache_clear` | Clear the web cache | -- |
| `docs_reindex` | Force re-index of a library's docs | `key` = library name (required) |
| `warmup` | Pre-download models (SearXNG, Playwright, ONNX embed/rerank) | -- |
| `setup_sync` | Configure Google Drive docs sync via OAuth Device Code flow | `remote_type` (default `drive`) |
| `setup_status` | Show current credential state and which providers are configured | -- |
| `setup_skip` | Opt into local-only mode (ONNX embed/rerank, no cloud keys) | -- |
| `setup_reset` | Clear all credentials and reset state | -- |
| `setup_complete` | Re-resolve credentials from the environment (re-inits embedding/reranker) | -- |

## help

Get full documentation for any tool. Not wrapped as external content.

| Parameter | Values |
|---|---|
| `tool_name` | `search` \| `extract` \| `media` \| `config` |

## config__open_relay

Opens the HTTP relay/credential setup form in the user's browser (self-host HTTP mode only; returns `stdio_unsupported` under stdio). No parameters.
