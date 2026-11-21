# WET (Web Extended Toolkit) -- Tools Reference

wet exposes 5 tools: 3 multiplexed capability tools (`search`, `extract`, `media`), each driven by an `action` parameter, plus `config` (server management) and `help` (full per-tool docs). Results from `search`, `extract`, and `media` are wrapped in an XPIA safety marker -- boundary tags plus an instruction to treat the content as data, not commands -- since they return externally-fetched web content.

## search

Find information across the web, academic sources, or indexed library documentation. Returns result listings (titles, URLs, snippets) -- not full page content. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `search` | Web search through the `SEARCH_BACKENDS` chain (default `tavily,duckduckgo`; keyed providers, optional-key Firecrawl/Keenable, credential-free DuckDuckGo/Startpage, or an opt-in `searxng`: an external `SEARXNG_URL`, or a local instance with `WET_AUTO_SEARXNG=true`) | `query` (required), `categories` (`general`\|`images`\|`videos`\|`files`), `max_results` (default 10), `time_range` (`day`\|`week`\|`month`\|`year`), `language`, `region` (2-letter country code), `include_domains` (max 5) / `exclude_domains` (max 10), `expand` (LLM query expansion), `enrich` (fetch real snippets), `refine` (re-query up to 2 times with LLM-rewritten terms when results are empty or low-relevance) |
| `research` | Academic/scientific search through the configured `SEARCH_BACKENDS` chain with `categories=science` | `query` (required), `max_results`, `time_range`, `language`, `include_domains` / `exclude_domains` |
| `docs` | Search library documentation, auto-indexing on first query | `library` (required), `query` (required), `language`, `version`, `limit` |
| `docs_resolve` | Free-form library name -> ranked `library_id` list | `query` (library name, required), `limit` |
| `docs_query` | Version-aware docs query honoring a project's locked library set + token cap | `library` (required), `query` (required), `version`, `topic`, `project_path`, `limit` |
| `docs_lock_project` | Detect project manifests (pyproject/package.json/go.mod/Cargo.toml) and lock the library set for isolation (Cabinets) | `project_path` (required) |
| `similar` | Find pages similar to a URL | `query` = full http(s) URL (required), `max_results` |

Search and research results are cached for one hour; a `search` with `time_range` is cached for five minutes. Every response carries a `search_backend` trace (requested, attempted, selected, and a `fallback` state of `none`, `used`, `exhausted`, `unavailable`, or `parallel_fanout`). The web-search fallbacks used by `research`, `similar`, and docs discovery use the same configured backend chain. `docs_query` returns `status: "indexing_in_progress"` while a library is still being indexed in the background. `expand` needs a configured `[models.chat]` cell; `similar` uses it for keyword extraction and falls back to the page title without one.

## extract

Read and return full page content from URLs or local files. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `extract` | Get clean content from URLs (markdown/text/html) | `urls` (required, max 20), `format`, `stealth` (anti-bot bypass) |
| `batch` | Batch extract with per-domain rate limiting | `urls` (required, max 50) |
| `crawl` | Deep crawl following links from root URLs | `urls` (required), `depth` (default 2, max 5), `max_pages` (default 20, max 100) |
| `map` | Discover site URL structure without extracting content | `urls` (required), `depth`, `max_pages` |
| `convert` | Convert local files (PDF, DOCX, PPTX, XLSX, CSV, JSON, XML, HTML, EPUB, TXT, image EXIF) to Markdown | `paths` (required absolute paths, max 10) |
| `extract_structured` | Extract structured data from a page using a JSON Schema + LLM | `urls` (required), `schema` (required JSON Schema dict), `prompt` |
| `agent` | Multi-step research orchestration: search the web, extract top results, synthesize a cited Markdown answer | `query` (required), `max_urls` (default 5, hard cap 20), `synthesis_model`, `token_budget` (default 10000) |
| `interact` | Drive a page with click/fill/submit via a browser automation session | `url` (required), `actions` (required list of `{type, selector?, description?, value?}`), `session` (persistent session id), `screenshot` |
| `diff` | Track content changes across fetches of the same URL(s) | `urls` (required), `refetch` (default `true` -- fetch a fresh copy before comparing; set `false` to compare already-recorded snapshots without a new network fetch) |

`extract`, `crawl`, and `map` results are cached for one day. `batch` fetches at most 2 pages concurrently per domain, 1 request per second per domain, and 10 globally.

`convert` reads only paths inside the allowed directories: by default the server's working directory and its temp directory, or the directories listed in `CONVERT_ALLOWED_DIRS`. `extract_structured` and `agent` need a configured `[models.chat]` cell.

`BROWSER_BACKENDS` selects the page renderer used when extraction escalates (`native`, `browserless`, `invisible`). It does not route `interact`: that action uses native Patchright browser sessions and requires their local runtime. Screenshots from `interact` are saved under `~/.wet/interact/`.

`diff` requires the web cache enabled (`WET_CACHE=true`). Returns per-URL `change_status` (`new`\|`same`\|`changed`) plus a unified `diff` (empty when unchanged) and `old_fetched_at`/`new_fetched_at` timestamps.

## media

Discover and download media files (images, videos, audio) from web pages. Wrapped as external content.

| Action | Purpose | Key parameters |
|---|---|---|
| `list` | Scan a page and return media URLs with metadata | `url` (required), `media_type` (`images`\|`videos`\|`audio`\|`files`\|`all`), `max_items` (default 10) |
| `download` | Download media files to local storage | `media_urls` (required), `output_dir` (must resolve within the configured download directory, default `~/.wet/downloads`) |

This server lists and downloads media; vision/audio/video analysis of it is out of scope.

## config

Server configuration and management, not wrapped as external content. Auth, models, and storage are host-owned: edit `~/.wet/config.toml` and restart the server; there is no setup wizard.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show auth mode and bind, docs database stats and indexing state, embedding/reranker backend, cache, runtime settings, and search metrics | -- |
| `set` | Update a runtime setting (`log_level`, `tool_timeout`, `wet_cache`, `wet_search_budget`) | `key`, `value` (required) |
| `cache_clear` | Clear the web cache (in `multi` auth mode, only the caller's namespace) | -- |
| `docs_reindex` | Force re-index of a library's docs | `key` = library name (required), for example `{"action": "docs_reindex", "key": "fastapi"}` |
| `warmup` | First-run setup (Playwright browsers; SearXNG install only when `WET_AUTO_SEARXNG` is on), then a cloud model probe; if no cloud cell is ready, downloads the local embedding model and, when reranking is enabled, the local reranker | -- |

## help

Get full documentation for any tool. Not wrapped as external content.

| Parameter | Values |
|---|---|
| `tool_name` | `search` \| `extract` \| `media` \| `config` |
