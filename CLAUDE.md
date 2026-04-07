# claude-plugins

Claude Code plugin marketplace and registry for n24q02m plugins.

## Structure

- `plugins/` -- individual plugin directories (synced from source repos)
- `.claude-plugin/marketplace.json` -- plugin registry manifest
- `scripts/sync-plugins.sh` -- sync plugins from upstream repos
- `scripts/validate_marketplace.py` -- validate registry structure and plugin integrity
- `scripts/test_validate_marketplace.py` -- unit tests for the validation script

## Plugins

- wet-mcp
- mnemo-mcp
- better-notion-mcp
- better-telegram-mcp
- better-email-mcp
- better-godot-mcp
- better-code-review-graph

## Conventions

- Plugin manifests live in each plugin subdirectory
- Sync script pulls latest from source repos -- do not edit plugin files directly
- Renovate manages dependency updates
- All changes via PR with conventional commits
