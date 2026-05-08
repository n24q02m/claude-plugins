# Agent Collaboration

## Quick reference

- Repo: `n24q02m/claude-plugins`
- Description: 8 MCP servers for Claude Code, Codex, and other AI coding agents.
- License: MIT

## Build & Test

See [README.md](README.md) for end-user install. For development:

```sh
mise run setup     # First-time dev environment
mise run lint      # Read-only lint + format check + type check
mise run test      # Run tests
mise run fix       # Auto-fix lint + format
```

## Release

Releases triggered manually via `workflow_dispatch` on `cd.yml`. Choose `beta` or `stable`. python-semantic-release handles version bump, CHANGELOG, tag, and GitHub Release.

## Conventions

- Commits: only `feat:` and `fix:` prefixes (enforced by pre-commit `commit-msg` hook)
- Test coverage: ≥ 95% on internal modules
- No secrets in code, commits, or memory — use [skret](https://skret.n24q02m.com) for secret retrieval
