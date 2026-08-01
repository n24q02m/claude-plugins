# Agent Collaboration

## Quick reference

- Repo: `n24q02m/claude-plugins`
- Description: 9 MCP servers for Claude Code, Codex, and other AI coding agents.
- License: Apache-2.0

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
- `plugins/<repo>/` is generated. `scripts/sync-plugins.sh` replaces `plugin.json`, `gemini-extension.json`, `skills/`, `hooks/`, `commands/` and `chat.py` from the source repository on every release, so a patch to those paths is erased at that plugin's next release — open it against the source repo instead. The setup prose alongside them is not generated and is edited here.
- Decisions on proposals, accepted and rejected, are recorded in `.jules/bolt.md`, `.jules/palette.md` and `.jules/sentinel.md`. Read the relevant one before proposing a change, so a settled question is not reopened.
