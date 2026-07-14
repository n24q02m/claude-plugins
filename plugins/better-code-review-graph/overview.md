# Better Code Review Graph -- Overview

A persistent, incremental knowledge graph of a codebase, exposed to an AI agent for token-efficient, impact-aware code review. Ask "who calls this?", "what does this change break?", and "review my diff" without pasting whole files into the prompt.

## What it does

- **Graph**: parse source into a call/import/inheritance graph, update incrementally, embed nodes for semantic search, and export/import a portable graph artifact (build on CI, import on a laptop).
- **Query**: predefined relationship queries (callers, callees, imports, tests, inheritors), name/keyword/vector search, and blast-radius impact analysis from changed files.
- **Review**: auto-detect changed files from a git diff and return a structural summary, impacted nodes, and source snippets as review context.
- **Security**: scan graph nodes with a heuristic or Semgrep engine and emit JSON or SARIF reports.

## Tools

Domain tools `graph`, `query`, `review`, and `security`, each driven by an `action` parameter, plus the universal `config` (status, runtime settings, credential setup) and `help`; `config__open_relay` reopens the browser credential form. Every action and parameter is listed in the [tools reference](/servers/better-code-review-graph/tools/).

## Clients

Defaults to `stdio` and runs against a local checkout; it ships Docker `:http` builds for advanced self-host but has no hosted remote-relay mode by default. Works with any stdio MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. See the [modes overview](/get-started/modes-overview/).

## Configuration

The graph, heuristic security scan, and most queries work with no credentials. Optional cloud embeddings and LLM node summaries are unlocked with your own keys and model chains, all supplied as environment variables:

- `EMBEDDING_MODELS`, `SUMMARY_MODELS` -- optional CSV model chains for node embeddings and function summaries; empty falls back to the bundled local model or disables the feature.
- Provider API keys (`JINA_AI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`).

Use placeholders in shared config and never commit real keys. Full walkthrough in [setup](/servers/better-code-review-graph/setup/).

## Next steps

- [Setup](/servers/better-code-review-graph/setup/) -- install and configure
- [Tools reference](/servers/better-code-review-graph/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-code-review-graph/troubleshooting/)
