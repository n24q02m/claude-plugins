---
title: Server comparison
description: Side-by-side comparison of all 9 servers in the stack.
---

| Server | Tools | Default mode | Multi-user | Docker | Language | License |
|---|---:|---|:-:|:-:|---|---|
| `mcp-core` | — | (foundation lib) | — | — | TypeScript + Python | MIT |
| `wet-mcp` | 4 + 2 | `local-relay` | yes (relay) | GHCR | Python | MIT |
| `mnemo-mcp` | 5 + 2 | `local-relay` | yes (relay) | GHCR | Python | MIT |
| `better-code-review-graph` | 5 + 2 | `local-relay` | yes (relay) | GHCR | Python | MIT |
| `imagine-mcp` | 4 + 2 | `local-relay` | yes (relay) | GHCR | Python | MIT |
| `better-telegram-mcp` | 6 + 2 | `remote-relay` | yes (relay+OAuth) | GHCR | Python | MIT |
| `better-notion-mcp` | 7 + 2 | `remote-oauth` | yes (relay+OAuth) | GHCR | TypeScript | MIT |
| `better-email-mcp` | 6 + 2 | `remote-relay` | yes (relay+OAuth) | GHCR | TypeScript | MIT |
| `better-godot-mcp` | 19 + 2 | `stdio` | no | GHCR | TypeScript | MIT |

(N + 2 = N domain tools plus the universal `help` and `config` tools — see [tool layout standard](/reference/tool-layout-standard/).)

## At a glance

- **Most servers default to `local-relay`** — single-user browser flow, simplest first-run UX.
- **Notion / Email / Telegram default to remote** — team-shared deploy is the common scenario for these.
- **Godot defaults to `stdio`** — no credentials needed, just a Godot-engine spawn.
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

## Versioning

Each server cuts independent releases (`vMAJOR.MINOR.PATCH`). All servers depend on `mcp-core` — major version bumps in `mcp-core` propagate as bumps to all consumers. See each server's CHANGELOG.

## License

All 9 repos are MIT-licensed. Forks and self-host welcome — no license fees, no telemetry phoning home.

## See also

- [Mode matrix](/reference/mode-matrix/)
- [Tool layout standard](/reference/tool-layout-standard/)
- [Multi-user pattern](/reference/multi-user-pattern/)
