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

## Renaming a tool in a server

`plugins/<repo>/tools.md` is the only place a tool name is written down for the
public. The marketplace listing and `mcp.n24q02m.com/servers/<repo>/tools/` both
read it, and nothing generates it: `plugin.json` carries no tool list, and the
sync described above never copies `.md` files. A rename in a server is therefore
invisible here until somebody types it, and until they do, the docs name tools
the server no longer answers to.

### Who starts the update

The server repo, not this one. Every server already notifies this repo on
release (`repository_dispatch: plugin-sync`), and the session that renames a
tool opens the companion `tools.md` pull request here. This repo does not scrape
server repos for prose — it verifies what it was handed, and sweeps weekly so a
rename that nobody reported still surfaces.

### When it has to land

**Before the server's stable release, not after.** Betas are safe to run ahead:
`cd.yml` accepts only `vX.Y.Z` tags, so a prerelease never reaches the
marketplace. A stable tag does, within minutes.

Order:

1. Server repo: rename, merge to `main`, cut a beta.
2. Here: open the `tools.md` pull request. Check it against the beta before the
   stable tag exists — `python3 scripts/verify_tool_parity.py <repo> --version <beta-version>`,
   or run the Tool Parity workflow with the same inputs.
3. Merge it.
4. Server repo: cut the stable release. The sync lands, and the parity check on
   `main` confirms the two agree.

Doing 4 before 3 is the failure this ordering exists to prevent. It is not fatal
— the check on `main` goes red and the weekly sweep would catch it anyway — but
between the release and the fix, the published docs are wrong.

### What enforces it

`scripts/verify_tool_parity.py` asks the server instead of trusting the prose:
it launches the exact command from `plugin.json` over stdio, calls MCP
`tools/list`, and diffs those names against the ones `tools.md` declares (an
`## <tool>` heading, or the first column of a table headed `Tool`).
`.github/workflows/tool-parity.yml` runs it on pull requests touching
`plugins/*/tools.md` or `plugins/*/.claude-plugin/plugin.json`, on the matching
pushes to `main`, weekly, and on demand.

Two things to know before changing it:

- Not every server can be read from a public runner. `wet-mcp`, `mnemo-mcp`,
  `better-godot-mcp` and `better-code-review-graph` answer `tools/list` with no
  credentials at all. Others exit at startup unless a credential is present; for
  those the checker retries once with an obviously fake value, which is enough
  when the server only checks that something is set (`better-notion-mcp`). A
  server that *validates* its credential on startup — `better-telegram-mcp`
  reaches the Bot API and dies — cannot be read here at all. That case is
  reported as a warning, never a silent pass, and its drift check belongs in
  that server's own CI, which has real credentials. Real credentials are never
  needed here and must never be added to this repo's CI.
- `--declared-only` runs the same comparison's static half with no network, which
  is enough to check that a `tools.md` edit is still parseable.

`scripts/verify_docs_current.py` remains the static neighbour: it checks that the
required pages exist and that every `userConfig` key is documented. It does not
look at tool names.
