# Better Code Review Graph -- Troubleshooting

Common issues specific to better-code-review-graph (crg). For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx better-code-review-graph@<X.Y.0bN>
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Query or review returns nothing

The graph is built on demand -- run a build before querying:

```
graph(action="build")
```

`review(action="context")` and `query(action="impact")` need a populated graph; on an empty graph they return no impacted nodes.

## Embeddings unavailable

Vector search and node summaries need either the bundled local model or a cloud provider key. With no `EMBEDDING_MODELS`/`SUMMARY_MODELS` chain and no provider key configured, the server falls back to the local model; if that fails to download, set a provider key (`GEMINI_API_KEY`, `JINA_AI_API_KEY`, `OPENAI_API_KEY`, or `COHERE_API_KEY`).

## Security scan finds nothing / wrong engine

`security(action="scan")` defaults to the `heuristic` engine. For deeper rules, pass `engine="semgrep"` (Semgrep must be installed). Use `security(action="rule_list")` to see active rules and `suppress` to mute a noisy one.

## Credentials or settings not saving

- crg defaults to stdio; there is no hosted relay. `config__open_relay` returns `stdio_unsupported` under stdio. Set keys as environment variables or `userConfig` fields.
- Check state with `config(action="setup_status")` and reset with `config(action="setup_reset")` if it seems stuck.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/better-code-review-graph/setup/).

## Filing a bug

Open an issue on [n24q02m/better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) with your OS, server version, transport mode, and the last 50 lines of stderr.
