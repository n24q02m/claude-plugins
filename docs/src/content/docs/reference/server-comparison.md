---
title: Server comparison
description: Side-by-side comparison of all 9 servers in the stack, plus the mcp-core foundation library.
---

| Server | Tools | Default mode | Multi-user | Container distribution | Language | License |
|---|---:|---|:-:|---|---|---|
| `mcp-core` | — | (foundation lib) | — | — | TypeScript + Python | Apache-2.0 |
| `wet-mcp` | 4 + 2 | `stdio` | yes (relay) | Source build | Python | Apache-2.0 |
| `mnemo-mcp` | 5 + 2 | `stdio` | yes (relay) | Source build | Python | Apache-2.0 |
| `better-code-review-graph` | 5 + 2 | `stdio` | yes (relay) | Source build | Python | Apache-2.0 |
| `imagine-mcp` | 4 + 2 | `stdio` | yes (relay) | GHCR | Python | Apache-2.0 |
| `better-telegram-mcp` | 6 + 2 | `stdio` | yes (relay+OAuth) | GHCR | Python | Apache-2.0 |
| `better-notion-mcp` | 7 + 2 | `stdio` | yes (relay+OAuth) | GHCR | TypeScript | Apache-2.0 |
| `better-email-mcp` | 6 + 2 | `stdio` | yes (relay+OAuth) | GHCR | TypeScript | Apache-2.0 |
| `better-godot-mcp` | 19 + 2 | `stdio` | no | GHCR | TypeScript | Apache-2.0 |
| `better-workspace-mcp` | 11 + 2 | `stdio` | yes (OAuth) | GHCR | TypeScript | Apache-2.0 |

(N + 2 = N domain tools plus the universal `help` and `config` tools — see [tool layout standard](/reference/tool-layout-standard/).)

## At a glance

- **Every marketplace plugin defaults to `stdio`** — local install is the safe,
  portable baseline.
- **Relay/OAuth modes are explicit self-hosted overrides** — use them for
  multi-user or browser-auth scenarios.
- **Telegram's managed hosted runtime is retired** — local stdio and self-hosted
  HTTP remain supported.
- **Workspace OAuth differs by transport** — stdio uses a Desktop OAuth client;
  self-hosted HTTP uses a Web application client.
- **mcp-core is not a server** — it's the shared library every other server consumes (transport, OAuth AS, lifecycle, multi-user primitives).

## Which to install first?

For most users:

- **wet-mcp** — search the web. Useful in any agent context.
- **mnemo-mcp** — give the agent a long-term memory. Pairs with wet for "what did we discuss last week?" queries.
- **better-code-review-graph** — for code-aware workflows; provides token-efficient code-review context in agent calls.

For specific workflows:

- Coding in unfamiliar repo → `better-code-review-graph`
- Drafting docs/blog → `better-notion-mcp`
- Image / video tasks → `imagine-mcp`
- Telegram bot work → `better-telegram-mcp`
- Email triage → `better-email-mcp`
- Godot game dev → `better-godot-mcp`
- Google Docs / Drive / Calendar / Gmail → `better-workspace-mcp`

## Versioning

Each server cuts independent releases (`vMAJOR.MINOR.PATCH`). All servers depend on `mcp-core` — major version bumps in `mcp-core` propagate as bumps to all consumers. See each server's CHANGELOG.

`better-workspace-mcp` is still pre-1.0: it publishes beta artifacts only (`0.1.0-beta.x` on npm, `:beta` on the registries), with no stable tag yet.

## License

Every repo in the stack is **Apache-2.0**. Several started out MIT and keep the original terms alongside in a `LICENSE-MIT` file, as the MIT license requires; `LICENSE` is the one that governs. `better-workspace-mcp` has been Apache-2.0 from the start, because it vendors Apache-2.0 code from [gemini-cli-extensions/workspace](https://github.com/gemini-cli-extensions/workspace) and keeps that license for the whole repo.

Forks and self-host welcome — no license fees, no telemetry phoning home.

## See also

- [Mode matrix](/reference/mode-matrix/)
- [Tool layout standard](/reference/tool-layout-standard/)
- [Multi-user pattern](/reference/multi-user-pattern/)
