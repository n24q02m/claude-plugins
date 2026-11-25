# skret -- Troubleshooting

Common issues specific to `skret` and its MCP server.

## Command `skret` not found

Install `skret` onto `PATH` before launching Claude Code:

```bash
# macOS / Linux
brew install n24q02m/tap/skret

# Windows
scoop bucket add n24q02m https://github.com/n24q02m/scoop-bucket && scoop install skret
```

## Missing `.skret.yaml` in workspace

The SessionStart hook warns when `.skret.yaml` is absent in the working directory. Run `skret init` or `skret setup` in your repository root, or pass `--workdir <project>` to `skret mcp`.

## Write operations rejected (`allow_write` / `confirm`)

Write tools (`skret_set`, `skret_delete`, `skret_rotate`) refuse mutations unless:

1. `.skret.yaml` enables `mcp.allow_write: true` (and the MCP server is restarted), and
2. Each write tool call includes boolean `"confirm": true`.

## Non-loopback HTTP bind refused

When using `skret mcp --transport http` on a non-loopback `--addr`, set a bearer token via `--token` or `SKRET_MCP_TOKEN`.

## Filing a bug

Open an issue on [n24q02m/skret](https://github.com/n24q02m/skret) with your OS, `skret --version`, and provider backend.
