# Contributing to claude-plugins

## Development Setup

Install Bun, Node.js 24+, and Python 3.11+. The Astro project lives in `docs/`.
From that directory:

```bash
bun install --frozen-lockfile
bun run dev
```

`predev` and `prebuild` run `docs/scripts/sync-plugin-docs.mjs`. Author
per-plugin prose in `plugins/<name>/*.md`; edit shared reference/get-started
pages directly under `docs/src/content/docs/`. The ignored `servers/` content
tree and `docs/dist/` are generated outputs, not authoring locations.

Plugin manifests, Skills, hooks, commands, and Agent Chat runtime assets are
mirrored from the source repositories by `scripts/sync-plugins.sh` and the
release-sync workflow. That asset sync does **not** copy per-plugin prose.
Change mirrored assets in their source repository first.

From the repository root, run the relevant source checks:

```bash
python scripts/validate_marketplace.py
python scripts/verify_docs_current.py
python scripts/verify_tool_parity.py --all --declared-only
node --test docs/scripts/test-sync-plugin-docs.mjs
```

For a docs change, also run `bun run build` from `docs/`, then `bun run preview`
and inspect the changed routes, navigation, Pagefind results, and edit links.
A local render does not prove that the Cloudflare Pages deployment changed.

## Commit Convention

Only two prefixes allowed:
- `feat:` — new features
- `fix:` — bug fixes

## Pull Requests

- One PR per feature/fix
- Tests required (>=95% coverage)
- All CI checks must pass
