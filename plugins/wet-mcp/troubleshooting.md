# WET (Web Extended Toolkit) -- Troubleshooting

Common issues specific to wet-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx --python 3.13 wet-mcp@<X.Y.0bN>
```

Replace `<X.Y.0bN>` with the exact beta version (for example, the value shown on the package's release history). Drop back to `wet-mcp` with no version to return to the latest stable.

## Server fails to start on Python 3.14+

wet-mcp requires **Python 3.13** -- the bundled SearXNG search engine is not compatible with 3.14+. Always pin the interpreter:

```sh
uvx --python 3.13 wet-mcp
```

## First run is slow / downloads a lot

On first start the server downloads SearXNG, a Playwright browser, and local embedding/reranker models. Pre-download them instead of waiting on the first tool call:

```
config(action="warmup")
```

## SearXNG port conflict

If the embedded SearXNG port is already in use, move it:

```sh
export WET_SEARXNG_PORT=<alternate-port>
```

## Credentials or settings not saving

- Under stdio (the default plugin install), there is no browser relay form -- `config__open_relay` returns `stdio_unsupported`. Set credentials as environment variables or `userConfig` fields instead.
- In HTTP self-host mode, open the relay form and check state with `config(action="setup_status")`. If credentials seem stuck to an old session, reset with `config(action="setup_reset")` and re-submit.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint** (command string or URL), not by name. Installing the plugin *and* adding a Docker or HTTP override loads both and creates duplicates. Pick one method: uninstall the plugin (`/plugin uninstall wet-mcp@n24q02m-plugins`) before adding a `docker run` or HTTP override. See [setup](/servers/wet-mcp/setup/) for the full method matrix.

## Filing a bug

Open an issue on [n24q02m/wet-mcp](https://github.com/n24q02m/wet-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.
