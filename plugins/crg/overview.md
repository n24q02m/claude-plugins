# Better Code Review Graph -- Overview

A persistent, incremental knowledge graph of a codebase, exposed to an AI agent for token-efficient, impact-aware code review. Ask "who calls this?", "what does this change break?", and "review my diff" without pasting whole files into the prompt.

## What it does

- **Graph**: parse source into a call/import/inheritance graph, update incrementally, embed nodes for semantic search, and export/import a portable graph artifact (build on CI, import on a laptop).
- **Query**: predefined relationship queries (callers, callees, imports, tests, inheritors), name/keyword/vector search, and blast-radius impact analysis from changed files.
- **Review**: auto-detect changed files from a git diff and return a structural summary, impacted nodes, and source snippets as review context.
- **Security**: scan graph nodes with a heuristic or Semgrep engine and emit JSON or SARIF reports.

## Tools

Domain tools `graph`, `query`, `review`, and `security`, each driven by an `action` parameter, plus the universal `config` (status, runtime settings, model-cell setup state) and `help`. The same actions are available from the local `crg` CLI. Every action and parameter is listed in the [tools reference](/servers/crg/tools/).

## Clients

crg is local-first. It defaults to `stdio` and runs against a local checkout, and the CLI and bundled skills are the primary surface. Works with any stdio MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. HTTP is opt-in and self-host only: you run one instance (`crg server start`, or a container built from source) and authenticate clients with a Bearer token. There is no hosted endpoint. See the [modes overview](/get-started/modes-overview/).

## Configuration

The graph, heuristic security scan, and most queries work with no configuration. Optional cloud embeddings and LLM node summaries are unlocked through the host-owned instance config and a few environment variables:

- `EMBEDDING_MODELS` -- optional CSV of embedding models; the first entry is active. Empty falls back to the bundled local model.
- `HULL_EMBED_API_KEY`, `HULL_CHAT_API_KEY` -- optional keys for the `[models.embed]` and `[models.chat]` provider cells. Node summaries need a configured chat cell; without one they are skipped.
- `LOCAL_EMBEDDING_MODEL` and its metadata fields, `LOCAL_RERANK_MODEL` -- optional local embedding and reranking models.

crg does not read per-vendor key variables such as `OPENAI_API_KEY`. Use placeholders in shared config and never commit real keys. Full walkthrough in [setup](/servers/crg/setup/).

## Next steps

- [Setup](/servers/crg/setup/) -- install and configure
- [Tools reference](/servers/crg/tools/) -- every action and parameter
- [Troubleshooting](/servers/crg/troubleshooting/)
