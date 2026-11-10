# claude-plugins

Claude Code plugin marketplace and registry for n24q02m plugins.

## Structure

- `plugins/` -- individual plugin directories (synced from source repos)
- `.claude-plugin/marketplace.json` -- plugin registry manifest
- `scripts/sync-plugins.sh` -- sync plugins from upstream repos

## Plugins

- wet
- mnemo
- notion
- telegram
- email
- crg
- workspace

## Conventions

- Plugin manifests live in each plugin subdirectory
- Sync script pulls latest from source repos -- do not edit plugin files directly
- Renaming a tool in a server: the `tools.md` update lands here **before** that
  server's stable release. Mechanism, ordering and the parity check in
  [AGENTS.md](AGENTS.md#renaming-a-tool-in-a-server)
- Renovate manages dependency updates
- All changes via PR with conventional commits
